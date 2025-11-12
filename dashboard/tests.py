from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from accounts.models import UserProfile
from wallet.models import Wallet, Transaction
from vps.models import VPSInstance, VPSPlan
from billing.models import BillingCycle, Invoice


class DashboardViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        # Create UserProfile
        UserProfile.objects.create(user=self.user, phone='1234567890')

        # Create wallet
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.00'))

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
        self.vps = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-instance-1',
            status='active',
            expires_at=timezone.now() + timedelta(days=30),
            ip_address='192.168.1.1'
        )

        # Create billing cycle
        self.billing_cycle = BillingCycle.objects.create(
            user=self.user,
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=30)).date(),
            amount=Decimal('20.00'),
            status='active'
        )

        # Create invoice
        self.invoice = Invoice.objects.create(
            user=self.user,
            billing_cycle=self.billing_cycle,
            invoice_number='INV-20231112-0001',
            amount=Decimal('20.00'),
            status='unpaid',
            due_date=(timezone.now() + timedelta(days=30)).date()
        )

        # Create transactions
        Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal('50.00'),
            transaction_type='deposit',
            status='completed',
            description='Test deposit'
        )
        Transaction.objects.create(
            wallet=self.wallet,
            amount=Decimal('10.00'),
            transaction_type='withdraw',
            status='completed',
            description='Test withdraw'
        )

    def test_dashboard_view_authenticated(self):
        """Test dashboard view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/dashboard.html')

        # Check context data
        self.assertEqual(response.context['wallet_balance'], Decimal('100.00'))
        self.assertEqual(response.context['active_vps_count'], 1)
        self.assertEqual(response.context['total_vps_count'], 1)
        self.assertEqual(response.context['monthly_cost'], Decimal('20.00'))
        self.assertEqual(response.context['pending_invoices_count'], 1)
        self.assertEqual(response.context['upcoming_expirations'], 0)  # Not expiring soon
        self.assertFalse(response.context['low_balance_warning'])

        # Check recent transactions (should have 2)
        self.assertEqual(len(response.context['recent_transactions']), 2)
        # Check recent vps
        self.assertEqual(len(response.context['recent_vps']), 1)
        # Check recent invoices
        self.assertEqual(len(response.context['recent_invoices']), 1)

    def test_dashboard_view_unauthenticated(self):
        """Test dashboard view redirects for unauthenticated user"""
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_dashboard_view_no_wallet(self):
        """Test dashboard view when user has no wallet"""
        self.wallet.delete()
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wallet_balance'], 0)

    def test_dashboard_view_no_vps(self):
        """Test dashboard view when user has no VPS instances"""
        VPSInstance.objects.filter(user=self.user).delete()
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_vps_count'], 0)
        self.assertEqual(response.context['total_vps_count'], 0)
        self.assertEqual(len(response.context['recent_vps']), 0)

    def test_dashboard_view_upcoming_expirations(self):
        """Test dashboard view with upcoming expirations"""
        self.vps.expires_at = timezone.now() + timedelta(days=3)
        self.vps.save()

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:dashboard'))

        self.assertEqual(response.context['upcoming_expirations'], 1)

    def test_dashboard_view_low_balance_warning(self):
        """Test dashboard view with low balance warning"""
        self.wallet.balance = Decimal('10.00')  # Less than monthly cost
        self.wallet.save()

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:dashboard'))

        self.assertTrue(response.context['low_balance_warning'])

    def test_profile_view_get(self):
        """Test profile view GET request"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/profile.html')

    def test_profile_view_post_valid_data(self):
        """Test profile view POST with valid data"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone': '0987654321'
        }
        response = self.client.post(reverse('dashboard:profile'), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('dashboard:profile'))

        # Check user updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertEqual(self.user.email, 'john@example.com')

        # Check profile updated
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.phone, '0987654321')

    def test_profile_view_post_partial_data(self):
        """Test profile view POST with partial data"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'first_name': 'Jane',
            'email': 'jane@example.com'
        }
        response = self.client.post(reverse('dashboard:profile'), data)

        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jane')
        self.assertEqual(self.user.email, 'jane@example.com')
        self.assertEqual(self.user.last_name, 'User')  # Unchanged

    def test_profile_view_unauthenticated(self):
        """Test profile view redirects for unauthenticated user"""
        response = self.client.get(reverse('dashboard:profile'))
        self.assertEqual(response.status_code, 302)

    def test_settings_view_get(self):
        """Test settings view GET request"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:settings'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/settings.html')

    def test_settings_view_password_change_valid(self):
        """Test settings view password change with valid data"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'action': 'change_password',
            'current_password': 'testpass123',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        }
        response = self.client.post(reverse('dashboard:settings'), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:login'))

        # Check password changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))

    def test_settings_view_password_change_wrong_current(self):
        """Test settings view password change with wrong current password"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'action': 'change_password',
            'current_password': 'wrongpass',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        }
        response = self.client.post(reverse('dashboard:settings'), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('dashboard:settings'))

        # Password should not change
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('testpass123'))

    def test_settings_view_password_change_mismatch(self):
        """Test settings view password change with mismatched passwords"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'action': 'change_password',
            'current_password': 'testpass123',
            'new_password': 'newpass123',
            'confirm_password': 'different123'
        }
        response = self.client.post(reverse('dashboard:settings'), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('dashboard:settings'))

        # Password should not change
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('testpass123'))

    def test_settings_view_password_change_too_short(self):
        """Test settings view password change with password too short"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'action': 'change_password',
            'current_password': 'testpass123',
            'new_password': '123',
            'confirm_password': '123'
        }
        response = self.client.post(reverse('dashboard:settings'), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('dashboard:settings'))

        # Password should not change
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('testpass123'))

    def test_settings_view_update_notifications(self):
        """Test settings view update notifications"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'action': 'update_notifications'
        }
        response = self.client.post(reverse('dashboard:settings'), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('dashboard:settings'))

    def test_settings_view_unauthenticated(self):
        """Test settings view redirects for unauthenticated user"""
        response = self.client.get(reverse('dashboard:settings'))
        self.assertEqual(response.status_code, 302)

    def test_notifications_view_get(self):
        """Test notifications view GET request"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:notifications'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/notifications.html')
        self.assertEqual(response.context['notifications'], [])

    def test_notifications_view_unauthenticated(self):
        """Test notifications view redirects for unauthenticated user"""
        response = self.client.get(reverse('dashboard:notifications'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_view_multiple_vps(self):
        """Test dashboard view with multiple VPS instances"""
        # Create another VPS
        VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-instance-2',
            status='stopped',
            expires_at=timezone.now() + timedelta(days=60),
            ip_address='192.168.1.2'
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:dashboard'))

        self.assertEqual(response.context['active_vps_count'], 1)  # Only one active
        self.assertEqual(response.context['total_vps_count'], 2)

    def test_dashboard_view_multiple_invoices(self):
        """Test dashboard view with multiple invoices"""
        # Create another invoice
        Invoice.objects.create(
            user=self.user,
            billing_cycle=self.billing_cycle,
            invoice_number='INV-20231112-0002',
            amount=Decimal('15.00'),
            status='paid',
            due_date=(timezone.now() + timedelta(days=15)).date()
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:dashboard'))

        self.assertEqual(response.context['pending_invoices_count'], 1)  # Only one unpaid
        self.assertEqual(len(response.context['recent_invoices']), 2)

    def test_profile_view_post_invalid_email(self):
        """Test profile view POST with invalid email (should still work as Django allows)"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'invalid-email'
        }
        response = self.client.post(reverse('dashboard:profile'), data)

        # Django doesn't validate email format in model, so it should work
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'invalid-email')

    def test_dashboard_view_no_billing_cycle(self):
        """Test dashboard view when user has no active billing cycle"""
        BillingCycle.objects.filter(user=self.user).delete()

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:dashboard'))

        self.assertEqual(response.context['monthly_cost'], 0)
        self.assertIsNone(response.context['current_billing_cycle'])
