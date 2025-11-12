from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.management import call_command
from django.core.files.base import ContentFile
from decimal import Decimal
from unittest.mock import patch, MagicMock
from io import BytesIO
import datetime

from .models import BillingCycle, Invoice
from vps.models import VPSInstance, VPSPlan
from wallet.models import Wallet, Transaction
from .services import HourlyBillingService, NotificationService, InvoiceService, AutoRenewalService


class BillingTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create another user for access control tests
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )

        # Create VPS plan
        self.plan = VPSPlan.objects.create(
            name='Test Plan',
            cpu_cores=2,
            ram_gb=4,
            disk_gb=50,
            bandwidth_gb=1000,
            price_per_month=Decimal('20.00')
        )

        # Create VPS instance
        self.vps_instance = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-instance-123',
            status='active',
            expires_at=timezone.now() + datetime.timedelta(days=30),
            ip_address='192.168.1.1'
        )

        # Create wallet
        self.wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal('100.00')
        )

        # Create billing cycle
        self.billing_cycle = BillingCycle.objects.create(
            user=self.user,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + datetime.timedelta(days=30),
            amount=Decimal('20.00')
        )

        # Create invoice
        self.invoice = Invoice.objects.create(
            user=self.user,
            billing_cycle=self.billing_cycle,
            invoice_number='INV-20231101-0001',
            amount=Decimal('20.00'),
            due_date=timezone.now().date() + datetime.timedelta(days=30)
        )

    # Model Tests
    def test_billing_cycle_creation(self):
        """Test BillingCycle model creation and fields"""
        self.assertEqual(self.billing_cycle.user, self.user)
        self.assertEqual(self.billing_cycle.amount, Decimal('20.00'))
        self.assertEqual(self.billing_cycle.status, 'unpaid')
        self.assertIsNone(self.billing_cycle.paid_at)

    def test_billing_cycle_str(self):
        """Test BillingCycle string representation"""
        expected = f"{self.user.username} - {self.billing_cycle.start_date} to {self.billing_cycle.end_date} - {self.billing_cycle.amount}"
        self.assertEqual(str(self.billing_cycle), expected)

    def test_billing_cycle_create_billing_cycle(self):
        """Test BillingCycle.create_billing_cycle class method"""
        start_date = timezone.now().date()
        end_date = start_date + datetime.timedelta(days=30)
        amount = Decimal('15.00')

        cycle = BillingCycle.create_billing_cycle(self.user, start_date, end_date, amount)

        self.assertEqual(cycle.user, self.user)
        self.assertEqual(cycle.start_date, start_date)
        self.assertEqual(cycle.end_date, end_date)
        self.assertEqual(cycle.amount, amount)
        self.assertEqual(cycle.status, 'unpaid')

    def test_billing_cycle_mark_as_paid(self):
        """Test BillingCycle.mark_as_paid method"""
        self.assertEqual(self.billing_cycle.status, 'unpaid')
        self.assertIsNone(self.billing_cycle.paid_at)

        self.billing_cycle.mark_as_paid()

        self.assertEqual(self.billing_cycle.status, 'paid')
        self.assertIsNotNone(self.billing_cycle.paid_at)

    def test_invoice_creation(self):
        """Test Invoice model creation and fields"""
        self.assertEqual(self.invoice.user, self.user)
        self.assertEqual(self.invoice.amount, Decimal('20.00'))
        self.assertEqual(self.invoice.status, 'draft')
        self.assertEqual(self.invoice.invoice_number, 'INV-20231101-0001')

    def test_invoice_str(self):
        """Test Invoice string representation"""
        expected = f"Invoice {self.invoice.invoice_number} - {self.user.username} - {self.invoice.amount}"
        self.assertEqual(str(self.invoice), expected)

    def test_invoice_generate_invoice_number(self):
        """Test Invoice.generate_invoice_number method"""
        number = Invoice.generate_invoice_number()
        self.assertTrue(number.startswith('INV-'))
        self.assertEqual(len(number.split('-')), 3)

        # Test uniqueness
        number2 = Invoice.generate_invoice_number()
        self.assertNotEqual(number, number2)

    def test_invoice_calculate_hourly_cost(self):
        """Test Invoice.calculate_hourly_cost method"""
        # Monthly cost 20.00, hourly base = 20/720 ≈ 0.02778, with 10% margin ≈ 0.03056
        expected = Decimal('0.03')  # quantized to 0.01
        result = self.invoice.calculate_hourly_cost(self.vps_instance)
        self.assertEqual(result, expected)

    def test_invoice_calculate_total_cost(self):
        """Test Invoice.calculate_total_cost method"""
        instances = [self.vps_instance]
        hours = 2
        # 0.03 * 2 = 0.06
        expected = Decimal('0.06')
        result = self.invoice.calculate_total_cost(instances, hours)
        self.assertEqual(result, expected)

    # View Tests
    def test_billing_dashboard_view(self):
        """Test billing dashboard view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/billing/dashboard/')  # Assuming URL pattern

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'billing/dashboard.html')
        self.assertIn('billing_cycles', response.context)
        self.assertIn('invoices', response.context)
        self.assertIn('wallet_balance', response.context)
        self.assertIn('renewal_check', response.context)

    def test_invoice_detail_view(self):
        """Test invoice detail view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/billing/invoice/{self.invoice.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'billing/invoice_detail.html')
        self.assertEqual(response.context['invoice'], self.invoice)

    def test_invoice_detail_view_other_user(self):
        """Test invoice detail view access control"""
        self.client.login(username='otheruser', password='otherpass123')
        response = self.client.get(f'/billing/invoice/{self.invoice.id}/')

        self.assertEqual(response.status_code, 404)

    @patch('billing.services.InvoiceService.generate_invoice_pdf')
    def test_download_invoice_view(self, mock_generate_pdf):
        """Test download invoice view"""
        mock_pdf = BytesIO(b'fake pdf content')
        mock_generate_pdf.return_value = mock_pdf

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/billing/invoice/{self.invoice.id}/download/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_billing_history_view(self):
        """Test billing history view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/billing/history/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'billing/history.html')
        self.assertIn('invoices', response.context)
        self.assertIn('total_invoices', response.context)
        self.assertIn('paid_amount', response.context)
        self.assertIn('pending_amount', response.context)

    def test_billing_analytics_view(self):
        """Test billing analytics view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/billing/analytics/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'billing/analytics.html')
        self.assertIn('total_billed', response.context)
        self.assertIn('monthly_spending', response.context)

    # Service Tests
    def test_hourly_billing_service_calculate_hourly_cost(self):
        """Test HourlyBillingService.calculate_hourly_cost"""
        expected = Decimal('0.03')
        result = HourlyBillingService.calculate_hourly_cost(self.vps_instance)
        self.assertEqual(result, expected)

    @patch('billing.services.NotificationService.send_hourly_billing_notification')
    def test_hourly_billing_service_process_for_user_success(self, mock_notify):
        """Test successful hourly billing for user"""
        result = HourlyBillingService.process_hourly_billing_for_user(self.user, hours=1)

        self.assertTrue(result['success'])
        self.assertIn('Successfully billed', result['message'])
        self.assertEqual(result['total_deducted'], Decimal('0.03'))

        # Check wallet balance decreased
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('99.97'))

    def test_hourly_billing_service_process_for_user_insufficient_balance(self):
        """Test hourly billing with insufficient balance"""
        self.wallet.balance = Decimal('0.01')
        self.wallet.save()

        result = HourlyBillingService.process_hourly_billing_for_user(self.user, hours=1)

        self.assertFalse(result['success'])
        self.assertIn('Insufficient balance', result['message'])
        self.assertEqual(result['total_deducted'], Decimal('0'))

    def test_hourly_billing_service_process_for_user_no_wallet(self):
        """Test hourly billing when user has no wallet"""
        self.wallet.delete()

        result = HourlyBillingService.process_hourly_billing_for_user(self.user, hours=1)

        self.assertFalse(result['success'])
        self.assertIn('User wallet not found', result['message'])

    def test_hourly_billing_service_process_for_user_no_instances(self):
        """Test hourly billing when user has no active instances"""
        self.vps_instance.status = 'stopped'
        self.vps_instance.save()

        result = HourlyBillingService.process_hourly_billing_for_user(self.user, hours=1)

        self.assertTrue(result['success'])
        self.assertIn('No active VPS instances', result['message'])

    def test_hourly_billing_service_process_for_all_users(self):
        """Test processing hourly billing for all users"""
        results = HourlyBillingService.process_hourly_billing_for_all_users(hours=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['user'], 'testuser')
        self.assertTrue(results[0]['success'])

    @patch('django.core.mail.send_mail')
    def test_notification_service_send_low_balance_notification(self, mock_send_mail):
        """Test sending low balance notification"""
        NotificationService.send_low_balance_notification(self.user, Decimal('5.00'), Decimal('10.00'))

        mock_send_mail.assert_called_once()
        args = mock_send_mail.call_args[0]
        self.assertIn('Low Wallet Balance', args[0])
        self.assertIn(self.user.email, args[3])

    @patch('django.core.mail.send_mail')
    def test_notification_service_send_payment_due_notification(self, mock_send_mail):
        """Test sending payment due notification"""
        NotificationService.send_payment_due_notification(self.user, self.invoice)

        mock_send_mail.assert_called_once()
        args = mock_send_mail.call_args[0]
        self.assertIn('Payment Due', args[0])

    @patch('django.core.mail.send_mail')
    def test_notification_service_send_hourly_billing_notification(self, mock_send_mail):
        """Test sending hourly billing notification"""
        NotificationService.send_hourly_billing_notification(self.user, Decimal('1.00'), 2)

        mock_send_mail.assert_called_once()
        args = mock_send_mail.call_args[0]
        self.assertIn('Hourly Billing Completed', args[0])

    def test_notification_service_check_wallet_balance_for_renewal(self):
        """Test checking wallet balance for renewal"""
        result = NotificationService.check_wallet_balance_for_renewal(self.user)

        self.assertTrue(result['sufficient'])
        self.assertEqual(result['current_balance'], Decimal('100.00'))
        self.assertGreater(result['required_balance'], 0)

    def test_invoice_service_generate_invoice_pdf(self):
        """Test PDF generation for invoice"""
        pdf_buffer = InvoiceService.generate_invoice_pdf(self.invoice)

        self.assertIsInstance(pdf_buffer, BytesIO)
        self.assertGreater(pdf_buffer.tell(), 0)  # Buffer has content

    @patch('billing.services.InvoiceService.generate_invoice_pdf')
    def test_invoice_service_create_invoice_for_billing_cycle(self, mock_generate_pdf):
        """Test creating invoice for billing cycle"""
        mock_pdf = BytesIO(b'fake pdf')
        mock_generate_pdf.return_value = mock_pdf

        invoice = InvoiceService.create_invoice_for_billing_cycle(self.billing_cycle, [self.vps_instance])

        self.assertEqual(invoice.user, self.user)
        self.assertEqual(invoice.billing_cycle, self.billing_cycle)
        self.assertEqual(invoice.amount, self.billing_cycle.amount)
        self.assertIsNotNone(invoice.pdf_file)

    @patch('billing.services.NotificationService.send_renewal_success_notification')
    def test_auto_renewal_service_process_for_user_success(self, mock_notify):
        """Test successful auto renewal"""
        # Make instance expired
        self.vps_instance.expires_at = timezone.now() - datetime.timedelta(days=1)
        self.vps_instance.save()

        result = AutoRenewalService.process_auto_renewal_for_user(self.user)

        self.assertTrue(result['success'])
        self.assertEqual(result['renewed_count'], 1)
        self.assertEqual(result['suspended_count'], 0)

        # Check instance renewed
        self.vps_instance.refresh_from_db()
        self.assertGreater(self.vps_instance.expires_at, timezone.now())

        # Check wallet balance decreased
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('80.00'))  # 100 - 20

    @patch('billing.services.NotificationService.send_renewal_failure_notification')
    def test_auto_renewal_service_process_for_user_insufficient_funds(self, mock_notify):
        """Test auto renewal with insufficient funds"""
        # Make instance expired and wallet low
        self.vps_instance.expires_at = timezone.now() - datetime.timedelta(days=1)
        self.vps_instance.save()
        self.wallet.balance = Decimal('10.00')
        self.wallet.save()

        result = AutoRenewalService.process_auto_renewal_for_user(self.user)

        self.assertTrue(result['success'])
        self.assertEqual(result['renewed_count'], 0)
        self.assertEqual(result['suspended_count'], 1)

        # Check instance suspended
        self.vps_instance.refresh_from_db()
        self.assertEqual(self.vps_instance.status, 'suspended')

    def test_auto_renewal_service_process_for_all_users(self):
        """Test processing auto renewal for all users"""
        # Make instance expired
        self.vps_instance.expires_at = timezone.now() - datetime.timedelta(days=1)
        self.vps_instance.save()

        results = AutoRenewalService.process_auto_renewal_for_all_users()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['user'], 'testuser')
        self.assertTrue(results[0]['success'])

    # Management Command Tests
    @patch('billing.services.HourlyBillingService.process_hourly_billing_for_all_users')
    def test_process_hourly_billing_command(self, mock_process):
        """Test process_hourly_billing management command"""
        mock_process.return_value = [
            {'user': 'testuser', 'success': True, 'message': 'Billed $1.00', 'total_deducted': Decimal('1.00')}
        ]

        from io import StringIO
        out = StringIO()
        call_command('process_hourly_billing', stdout=out)

        output = out.getvalue()
        self.assertIn('Starting hourly billing', output)
        self.assertIn('Successful: 1', output)
        self.assertIn('Total Deducted: $1.00', output)

    @patch('billing.services.HourlyBillingService.process_hourly_billing_for_all_users')
    def test_process_hourly_billing_command_dry_run(self, mock_process):
        """Test process_hourly_billing command with dry run"""
        mock_process.return_value = []

        from io import StringIO
        out = StringIO()
        call_command('process_hourly_billing', '--dry-run', stdout=out)

        output = out.getvalue()
        self.assertIn('DRY RUN MODE', output)
        self.assertIn('This was a dry run', output)

    # Edge Cases and Validation Tests
    def test_billing_cycle_invalid_amount(self):
        """Test BillingCycle with invalid amount"""
        with self.assertRaises(Exception):  # Should raise validation error
            BillingCycle.objects.create(
                user=self.user,
                start_date=timezone.now().date(),
                end_date=timezone.now().date(),
                amount=Decimal('-10.00')
            )

    def test_invoice_invalid_amount(self):
        """Test Invoice with invalid amount"""
        with self.assertRaises(Exception):
            Invoice.objects.create(
                user=self.user,
                invoice_number='TEST-001',
                amount=Decimal('-5.00'),
                due_date=timezone.now().date()
            )

    def test_wallet_deposit_negative_amount(self):
        """Test wallet deposit with negative amount"""
        with self.assertRaises(Exception):
            self.wallet.deposit(Decimal('-10.00'))

    def test_wallet_withdraw_insufficient_balance(self):
        """Test wallet withdraw with insufficient balance"""
        with self.assertRaises(Exception):
            self.wallet.withdraw(Decimal('200.00'))

    def test_vps_instance_renew_expired(self):
        """Test renewing expired VPS instance"""
        self.vps_instance.expires_at = timezone.now() - datetime.timedelta(days=5)
        self.vps_instance.save()

        new_expiry = self.vps_instance.renew(days=10)

        self.assertGreater(new_expiry, timezone.now())
        self.assertEqual((new_expiry - timezone.now()).days, 9)  # Approximately 10 days from now

    def test_vps_instance_renew_active(self):
        """Test renewing active VPS instance"""
        original_expiry = self.vps_instance.expires_at
        new_expiry = self.vps_instance.renew(days=5)

        self.assertEqual(new_expiry, original_expiry + datetime.timedelta(days=5))

    def test_invoice_generate_number_uniqueness(self):
        """Test invoice number generation uniqueness"""
        numbers = set()
        for _ in range(10):
            num = Invoice.generate_invoice_number()
            self.assertNotIn(num, numbers)
            numbers.add(num)

    def test_hourly_billing_multiple_instances(self):
        """Test hourly billing with multiple VPS instances"""
        # Create another instance
        vps2 = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-instance-456',
            status='active',
            expires_at=timezone.now() + datetime.timedelta(days=30)
        )

        result = HourlyBillingService.process_hourly_billing_for_user(self.user, hours=1)

        self.assertTrue(result['success'])
        self.assertEqual(result['total_deducted'], Decimal('0.06'))  # 0.03 * 2

        # Check wallet
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('99.94'))  # 100 - 0.06

    def test_auto_renewal_multiple_instances(self):
        """Test auto renewal with multiple instances"""
        # Create another expired instance
        vps2 = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-instance-456',
            status='active',
            expires_at=timezone.now() - datetime.timedelta(days=1)
        )

        result = AutoRenewalService.process_auto_renewal_for_user(self.user)

        self.assertEqual(result['renewed_count'], 2)
        self.assertEqual(result['total_cost'], Decimal('40.00'))  # 20 * 2

        # Check wallet
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('60.00'))  # 100 - 40
