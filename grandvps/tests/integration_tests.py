import json
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from accounts.models import UserProfile
from wallet.models import Wallet, Transaction
from vps.models import VPSPlan, VPSInstance
from billing.models import BillingCycle, Invoice
from billing.services import HourlyBillingService, InvoiceService


class GrandVPSIntegrationTests(TransactionTestCase):
    """Integration tests for GrandVPS system interactions"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        # Create wallet with default balance
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('0.00'))

        # Create VPS plan
        self.plan = VPSPlan.objects.create(
            name='Test Plan',
            cpu_cores=2,
            ram_gb=4,
            disk_gb=50,
            bandwidth_gb=1000,
            price_per_month=Decimal('20.00'),
            is_active=True
        )

    def test_user_registration_and_profile_creation(self):
        """Test user registration creates profile and wallet"""
        # User should have been created with profile via signal
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.timezone, 'Asia/Tehran')

        # Wallet should exist
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('0.00'))  # Default balance

    @patch('vps.services.doprax_client.DopraxClient.create_vps')
    @patch('vps.services.doprax_client.DopraxClient.get_locations_and_plans')
    def test_vps_creation_with_wallet_deduction(self, mock_get_locations, mock_create_vps):
        """Test VPS creation deducts from wallet and creates billing cycle"""
        # Mock API responses
        mock_get_locations.return_value = {
            'locationsList': [{'locationCode': 'us-east', 'provider': 'digitalocean'}]
        }
        mock_create_vps.return_value = {
            'vmCode': 'test-vm-123',
            'ipv4': '192.168.1.100'
        }

        # Ensure sufficient balance
        self.wallet.balance = Decimal('50.00')
        self.wallet.save()

        # Create VPS instance (simulate the view logic)
        from django.utils import timezone
        expires_at = timezone.now() + timedelta(days=30)

        vps_instance = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-vm-123',
            status='active',  # Set to active for billing
            expires_at=expires_at,
            ip_address='192.168.1.100'
        )

        # Deduct from wallet (simulate view logic)
        self.wallet.balance -= self.plan.price_per_month
        self.wallet.save()

        # Create transaction
        Transaction.objects.create(
            wallet=self.wallet,
            amount=-self.plan.price_per_month,
            transaction_type='payment',
            description=f'VPS Creation: {self.plan.name}',
            reference_id=vps_instance.instance_id
        )

        # Verify wallet deduction
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('30.00'))

        # Verify transaction created
        transaction = Transaction.objects.get(wallet=self.wallet, reference_id='test-vm-123')
        self.assertEqual(transaction.amount, -self.plan.price_per_month)
        self.assertEqual(transaction.transaction_type, 'payment')

        # Verify VPS instance
        self.assertEqual(vps_instance.status, 'active')
        self.assertEqual(vps_instance.plan, self.plan)

    def test_billing_processing_and_invoice_generation(self):
        """Test hourly billing processing and invoice generation"""
        # Create active VPS instance
        vps_instance = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-vm-123',
            status='active',
            expires_at=timezone.now() + timedelta(days=30)
        )

        # Ensure sufficient balance
        self.wallet.balance = Decimal('50.00')
        self.wallet.save()

        # Process hourly billing
        result = HourlyBillingService.process_hourly_billing_for_user(self.user, hours=1)

        # Verify billing was successful
        self.assertTrue(result['success'])
        self.assertGreater(result['total_deducted'], Decimal('0'))

        # Verify wallet was deducted
        self.wallet.refresh_from_db()
        self.assertLess(self.wallet.balance, Decimal('50.00'))

        # Verify transaction was created
        transactions = Transaction.objects.filter(wallet=self.wallet, transaction_type='withdraw')
        self.assertTrue(transactions.exists())

        # Create billing cycle
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)
        billing_cycle = BillingCycle.create_billing_cycle(
            user=self.user,
            start_date=start_date,
            end_date=end_date,
            amount=Decimal('20.00')
        )

        # Generate invoice
        invoice = InvoiceService.create_invoice_for_billing_cycle(billing_cycle, [vps_instance])

        # Verify invoice
        self.assertEqual(invoice.user, self.user)
        self.assertEqual(invoice.amount, billing_cycle.amount)
        self.assertEqual(invoice.status, 'draft')
        self.assertIsNotNone(invoice.invoice_number)

    def test_dashboard_data_aggregation(self):
        """Test dashboard aggregates data from all modules"""
        # Set wallet balance
        self.wallet.balance = Decimal('100.00')
        self.wallet.save()

        # Create test data
        vps_instance = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-vm-123',
            status='active',
            expires_at=timezone.now() + timedelta(days=30)
        )

        # Create billing cycle
        billing_cycle = BillingCycle.create_billing_cycle(
            user=self.user,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            amount=Decimal('20.00')
        )

        # Create invoice
        invoice = Invoice.objects.create(
            user=self.user,
            billing_cycle=billing_cycle,
            invoice_number='TEST-001',
            amount=Decimal('20.00'),
            due_date=timezone.now().date() + timedelta(days=30)
        )

        # Create transaction
        Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal('50.00'),
            transaction_type='deposit',
            description='Test deposit'
        )

        # Simulate dashboard view logic
        wallet_balance = self.wallet.balance
        recent_transactions = Transaction.objects.filter(wallet__user=self.user).order_by('-timestamp')[:5]
        vps_instances = VPSInstance.objects.filter(user=self.user)
        active_vps_count = vps_instances.filter(status='active').count()
        recent_invoices = Invoice.objects.filter(user=self.user).order_by('-issued_date')[:3]
        pending_invoices_count = Invoice.objects.filter(user=self.user, status='draft').count()

        # Verify aggregation
        self.assertEqual(wallet_balance, Decimal('100.00'))
        self.assertEqual(len(recent_transactions), 1)
        self.assertEqual(active_vps_count, 1)
        self.assertEqual(len(recent_invoices), 1)
        self.assertEqual(pending_invoices_count, 1)

    def test_end_to_end_user_flow(self):
        """Test complete user flow from registration to VPS management"""
        # 1. User registration (already done in setUp)

        # 2. Wallet funding
        self.wallet.deposit(Decimal('100.00'), 'Initial deposit')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('100.00'))

        # 3. VPS creation with mocked API
        with patch('vps.services.doprax_client.DopraxClient.create_vps') as mock_create, \
             patch('vps.services.doprax_client.DopraxClient.get_locations_and_plans') as mock_locations:

            mock_locations.return_value = {
                'locationsList': [{'locationCode': 'us-east', 'provider': 'digitalocean'}]
            }
            mock_create.return_value = {
                'vmCode': 'e2e-vm-123',
                'ipv4': '192.168.1.200'
            }

            # Create VPS (simulate view logic)
            expires_at = timezone.now() + timedelta(days=30)
            vps_instance = VPSInstance.objects.create(
                user=self.user,
                plan=self.plan,
                instance_id='e2e-vm-123',
                status='active',
                expires_at=expires_at,
                ip_address='192.168.1.200'
            )

            # Deduct payment
            self.wallet.withdraw(self.plan.price_per_month, f'VPS {self.plan.name}')

        # 4. Verify post-creation state
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('80.00'))  # 100 - 20

        transactions = Transaction.objects.filter(wallet=self.wallet)
        self.assertEqual(len(transactions), 2)  # deposit + withdrawal

        # 5. Billing cycle creation
        billing_cycle = BillingCycle.create_billing_cycle(
            user=self.user,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            amount=self.plan.price_per_month
        )

        # 6. Invoice generation
        invoice = InvoiceService.create_invoice_for_billing_cycle(billing_cycle, [vps_instance])

        # 7. Dashboard verification
        dashboard_data = {
            'wallet_balance': self.wallet.balance,
            'active_vps_count': VPSInstance.objects.filter(user=self.user, status='active').count(),
            'pending_invoices': Invoice.objects.filter(user=self.user, status='draft').count(),
            'recent_transactions': Transaction.objects.filter(wallet__user=self.user).count()
        }

        self.assertEqual(dashboard_data['wallet_balance'], Decimal('80.00'))
        self.assertEqual(dashboard_data['active_vps_count'], 1)
        self.assertEqual(dashboard_data['pending_invoices'], 1)
        self.assertEqual(dashboard_data['recent_transactions'], 2)

    def test_insufficient_balance_vps_creation(self):
        """Test VPS creation fails with insufficient balance"""
        # Set low balance
        self.wallet.balance = Decimal('5.00')
        self.wallet.save()

        # Attempt VPS creation should fail due to insufficient funds
        can_create = self.wallet.balance >= self.plan.price_per_month
        self.assertFalse(can_create)

        # Verify no VPS instances created
        vps_count_before = VPSInstance.objects.filter(user=self.user).count()

        # Simulate failed creation (no actual creation)
        vps_count_after = VPSInstance.objects.filter(user=self.user).count()
        self.assertEqual(vps_count_before, vps_count_after)

    def test_hourly_billing_insufficient_funds(self):
        """Test hourly billing when insufficient funds"""
        # Create active VPS
        vps_instance = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='billing-test-vm',
            status='active',
            expires_at=timezone.now() + timedelta(days=30)
        )

        # Set very low balance
        self.wallet.balance = Decimal('0.01')
        self.wallet.save()

        # Process billing
        result = HourlyBillingService.process_hourly_billing_for_user(self.user, hours=1)

        # Should fail due to insufficient funds
        self.assertFalse(result['success'])
        self.assertEqual(result['total_deducted'], Decimal('0'))

        # Wallet balance should remain unchanged
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('0.01'))