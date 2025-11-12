from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.core.management import call_command
from django.core.exceptions import ImproperlyConfigured
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
import json

from .models import VPSPlan, VPSInstance
from .forms import VPSCreationForm, VPSActionForm
from .services.doprax_client import DopraxClient, DopraxAPIError
from wallet.models import Wallet, Transaction


class VPSPlanModelTest(TestCase):
    """Test cases for VPSPlan model"""

    def setUp(self):
        self.plan = VPSPlan.objects.create(
            name='Test Plan',
            cpu_cores=2,
            ram_gb=4,
            disk_gb=50,
            bandwidth_gb=1000,
            price_per_month=Decimal('10.00')
        )

    def test_plan_creation(self):
        """Test basic plan creation"""
        self.assertEqual(self.plan.name, 'Test Plan')
        self.assertEqual(self.plan.cpu_cores, 2)
        self.assertEqual(self.plan.ram_gb, 4)
        self.assertEqual(self.plan.disk_gb, 50)
        self.assertEqual(self.plan.bandwidth_gb, 1000)
        self.assertEqual(self.plan.price_per_month, Decimal('10.00'))
        self.assertTrue(self.plan.is_active)

    def test_plan_str(self):
        """Test string representation"""
        self.assertEqual(str(self.plan), 'Test Plan')

    def test_plan_defaults(self):
        """Test default values"""
        plan = VPSPlan.objects.create(
            name='Basic Plan',
            cpu_cores=1,
            ram_gb=2,
            disk_gb=20,
            bandwidth_gb=500,
            price_per_month=Decimal('5.00')
        )
        self.assertTrue(plan.is_active)

    def test_plan_inactive(self):
        """Test inactive plan"""
        self.plan.is_active = False
        self.plan.save()
        self.assertFalse(self.plan.is_active)


class VPSInstanceModelTest(TestCase):
    """Test cases for VPSInstance model"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.plan = VPSPlan.objects.create(
            name='Test Plan',
            cpu_cores=2,
            ram_gb=4,
            disk_gb=50,
            bandwidth_gb=1000,
            price_per_month=Decimal('10.00')
        )
        self.expires_at = timezone.now() + timedelta(days=30)
        self.vps = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-instance-123',
            status='active',
            expires_at=self.expires_at,
            ip_address='192.168.1.1'
        )

    def test_vps_creation(self):
        """Test basic VPS creation"""
        self.assertEqual(self.vps.user.username, 'testuser')
        self.assertEqual(self.vps.plan.name, 'Test Plan')
        self.assertEqual(self.vps.instance_id, 'test-instance-123')
        self.assertEqual(self.vps.status, 'active')
        self.assertEqual(self.vps.ip_address, '192.168.1.1')

    def test_vps_str(self):
        """Test string representation"""
        expected = "testuser - Test Plan - test-instance-123"
        self.assertEqual(str(self.vps), expected)

    def test_renew_active_vps(self):
        """Test renewing an active VPS"""
        new_expiry = self.vps.renew(days=15)
        expected_expiry = self.expires_at + timedelta(days=15)
        self.assertEqual(new_expiry, expected_expiry)
        self.vps.refresh_from_db()
        self.assertEqual(self.vps.expires_at, expected_expiry)

    def test_renew_expired_vps(self):
        """Test renewing an expired VPS"""
        past_time = timezone.now() - timedelta(days=5)
        self.vps.expires_at = past_time
        self.vps.save()
        new_expiry = self.vps.renew(days=10)
        expected_expiry = timezone.now() + timedelta(days=10)
        # Allow some tolerance for time difference
        self.assertAlmostEqual((new_expiry - expected_expiry).total_seconds(), 0, delta=1)

    def test_is_expired_false(self):
        """Test is_expired returns False for active VPS"""
        self.assertFalse(self.vps.is_expired())

    def test_is_expired_true(self):
        """Test is_expired returns True for expired VPS"""
        self.vps.expires_at = timezone.now() - timedelta(days=1)
        self.vps.save()
        self.assertTrue(self.vps.is_expired())

    def test_days_until_expiry_active(self):
        """Test days_until_expiry for active VPS"""
        days = self.vps.days_until_expiry()
        self.assertGreaterEqual(days, 29)
        self.assertLessEqual(days, 30)

    def test_days_until_expiry_expired(self):
        """Test days_until_expiry for expired VPS"""
        self.vps.expires_at = timezone.now() - timedelta(days=1)
        self.vps.save()
        days = self.vps.days_until_expiry()
        self.assertEqual(days, 0)

    def test_vps_status_choices(self):
        """Test status choices are valid"""
        valid_statuses = ['pending', 'active', 'stopped', 'suspended', 'terminated']
        for status in valid_statuses:
            vps = VPSInstance.objects.create(
                user=self.user,
                plan=self.plan,
                instance_id=f'test-{status}',
                status=status,
                expires_at=timezone.now() + timedelta(days=1)
            )
            self.assertEqual(vps.status, status)

    def test_unique_instance_id(self):
        """Test instance_id uniqueness constraint"""
        with self.assertRaises(Exception):  # IntegrityError
            VPSInstance.objects.create(
                user=self.user,
                plan=self.plan,
                instance_id='test-instance-123',  # Same as existing
                status='pending',
                expires_at=timezone.now() + timedelta(days=1)
            )


class VPSCreationFormTest(TestCase):
    """Test cases for VPSCreationForm"""

    def setUp(self):
        self.plan = VPSPlan.objects.create(
            name='Test Plan',
            cpu_cores=2,
            ram_gb=4,
            disk_gb=50,
            bandwidth_gb=1000,
            price_per_month=Decimal('10.00')
        )

    @patch('vps.forms.DopraxClient')
    def test_form_initialization_success(self, mock_client):
        """Test form initialization with successful API calls"""
        mock_client_instance = MagicMock()
        mock_client_instance.get_locations_and_plans.return_value = {
            'locationsList': [
                {'locationCode': 'us-east', 'name': 'US East', 'country': 'US', 'provider': 'DigitalOcean'}
            ]
        }
        mock_client_instance.get_operating_systems.return_value = {
            'DigitalOcean': [
                {'slug': 'ubuntu-20-04', 'name': 'Ubuntu 20.04'}
            ]
        }
        mock_client.return_value = mock_client_instance

        form = VPSCreationForm()
        self.assertIn('location', form.fields)
        self.assertIn('operating_system', form.fields)
        self.assertEqual(len(form.fields['location'].choices), 1)
        self.assertEqual(len(form.fields['operating_system'].choices), 1)

    @patch('vps.forms.DopraxClient')
    def test_form_initialization_api_error(self, mock_client):
        """Test form initialization with API errors"""
        mock_client.side_effect = DopraxAPIError("API Error")

        form = VPSCreationForm()
        self.assertEqual(form.fields['location'].choices, [('', 'Unable to load locations')])
        self.assertEqual(form.fields['operating_system'].choices, [('', 'Unable to load operating systems')])

    def test_form_valid_data(self):
        """Test form with valid data"""
        data = {
            'plan': self.plan.id,
            'location': 'us-east',
            'operating_system': 'ubuntu-20-04',
            'vm_name': 'test-vm'
        }
        form = VPSCreationForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['vm_name'], 'test-vm')

    def test_form_auto_generate_vm_name(self):
        """Test automatic VM name generation"""
        data = {
            'plan': self.plan.id,
            'location': 'us-east',
            'operating_system': 'ubuntu-20-04'
        }
        form = VPSCreationForm(data=data)
        self.assertTrue(form.is_valid())
        vm_name = form.cleaned_data['vm_name']
        self.assertTrue(vm_name.startswith('vps-'))
        self.assertEqual(len(vm_name), 16)  # 'vps-' + 8 hex chars

    def test_form_invalid_data(self):
        """Test form with invalid data"""
        data = {
            'plan': '',  # Invalid
            'location': 'us-east',
            'operating_system': 'ubuntu-20-04'
        }
        form = VPSCreationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('plan', form.errors)


class VPSActionFormTest(TestCase):
    """Test cases for VPSActionForm"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.plan = VPSPlan.objects.create(
            name='Test Plan',
            cpu_cores=2,
            ram_gb=4,
            disk_gb=50,
            bandwidth_gb=1000,
            price_per_month=Decimal('10.00')
        )
        self.vps = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-instance-123',
            status='active',
            expires_at=timezone.now() + timedelta(days=30)
        )

    def test_form_valid_action(self):
        """Test form with valid action"""
        data = {'action': 'start'}
        form = VPSActionForm(data=data, vps_instance=self.vps)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['action'], 'start')

    def test_form_invalid_action(self):
        """Test form with invalid action"""
        data = {'action': 'invalid'}
        form = VPSActionForm(data=data, vps_instance=self.vps)
        self.assertFalse(form.is_valid())

    def test_start_already_active_validation(self):
        """Test validation prevents starting already active VPS"""
        self.vps.status = 'active'
        self.vps.save()
        data = {'action': 'start'}
        form = VPSActionForm(data=data, vps_instance=self.vps)
        self.assertFalse(form.is_valid())
        self.assertIn('VPS is already running', str(form.errors))

    def test_stop_already_stopped_validation(self):
        """Test validation prevents stopping already stopped VPS"""
        self.vps.status = 'stopped'
        self.vps.save()
        data = {'action': 'stop'}
        form = VPSActionForm(data=data, vps_instance=self.vps)
        self.assertFalse(form.is_valid())
        self.assertIn('VPS is already stopped', str(form.errors))

    def test_action_on_terminated_vps(self):
        """Test validation prevents actions on terminated VPS"""
        self.vps.status = 'terminated'
        self.vps.save()
        for action in ['start', 'stop', 'restart']:
            data = {'action': action}
            form = VPSActionForm(data=data, vps_instance=self.vps)
            self.assertFalse(form.is_valid())
            self.assertIn('Cannot perform actions on terminated VPS', str(form.errors))


class DopraxClientTest(TestCase):
    """Test cases for DopraxClient service"""

    def setUp(self):
        self.client = DopraxClient()

    @patch('vps.services.doprax_client.settings')
    def test_init_missing_api_key(self, mock_settings):
        """Test initialization fails without API key"""
        mock_settings.DOPRAX_API_KEY = None
        with self.assertRaises(ImproperlyConfigured):
            DopraxClient()

    @patch('vps.services.doprax_client.requests.get')
    def test_make_request_get_success(self, mock_get):
        """Test successful GET request"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': 'test'}
        mock_get.return_value = mock_response

        result = self.client._make_request('GET', '/test/')
        self.assertEqual(result, {'data': 'test'})

    @patch('vps.services.doprax_client.requests.get')
    def test_make_request_get_error(self, mock_get):
        """Test GET request with API error"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_get.return_value = mock_response

        with self.assertRaises(DopraxAPIError):
            self.client._make_request('GET', '/test/')

    @patch('vps.services.doprax_client.requests.post')
    def test_make_request_post_success(self, mock_post):
        """Test successful POST request"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': 'created'}
        mock_post.return_value = mock_response

        result = self.client._make_request('POST', '/test/', {'key': 'value'})
        self.assertEqual(result, {'data': 'created'})

    @patch('vps.services.doprax_client.requests.get')
    def test_get_locations_and_plans(self, mock_get):
        """Test getting locations and plans"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': {'locationsList': []}}
        mock_get.return_value = mock_response

        result = self.client.get_locations_and_plans()
        self.assertEqual(result, {'locationsList': []})

    @patch('vps.services.doprax_client.requests.get')
    def test_get_operating_systems(self, mock_get):
        """Test getting operating systems"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'os_map': {'ubuntu': []}}
        mock_get.return_value = mock_response

        result = self.client.get_operating_systems()
        self.assertEqual(result, {'ubuntu': []})

    @patch('vps.services.doprax_client.requests.post')
    def test_create_vps(self, mock_post):
        """Test VPS creation"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': {'vmCode': 'vm-123'}}
        mock_post.return_value = mock_response

        result = self.client.create_vps('us-east', '2cpu-4gb', 'ubuntu', 'DO', 'test-vm')
        self.assertEqual(result, {'vmCode': 'vm-123'})

    @patch('vps.services.doprax_client.requests.get')
    def test_get_vps_status(self, mock_get):
        """Test getting VPS status"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': {'status': 'active'}}
        mock_get.return_value = mock_response

        result = self.client.get_vps_status('vm-123')
        self.assertEqual(result, {'status': 'active'})

    @patch('vps.services.doprax_client.requests.post')
    def test_execute_vps_command_valid(self, mock_post):
        """Test executing valid VPS command"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'msg': 'success'}
        mock_post.return_value = mock_response

        result = self.client.execute_vps_command('vm-123', 'turnon')
        self.assertEqual(result, {'msg': 'success'})

    def test_execute_vps_command_invalid(self):
        """Test executing invalid VPS command"""
        with self.assertRaises(ValueError):
            self.client.execute_vps_command('vm-123', 'invalid')

    @patch('vps.services.doprax_client.requests.get')
    def test_get_vps_network_info(self, mock_get):
        """Test getting VPS network info"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': {'ip': '1.2.3.4'}}
        mock_get.return_value = mock_response

        result = self.client.get_vps_network_info('vm-123')
        self.assertEqual(result, {'ip': '1.2.3.4'})

    @patch('vps.services.doprax_client.requests.get')
    def test_get_vps_traffic(self, mock_get):
        """Test getting VPS traffic data"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': {'traffic': '100GB'}}
        mock_get.return_value = mock_response

        result = self.client.get_vps_traffic('vm-123')
        self.assertEqual(result, {'traffic': '100GB'})

    @patch('vps.services.doprax_client.requests.post')
    def test_create_snapshot(self, mock_post):
        """Test creating VPS snapshot"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': {'snapshot_id': 'snap-123'}}
        mock_post.return_value = mock_response

        result = self.client.create_snapshot('vm-123', 'backup')
        self.assertEqual(result, {'snapshot_id': 'snap-123'})

    @patch('vps.services.doprax_client.requests.get')
    def test_list_snapshots(self, mock_get):
        """Test listing VPS snapshots"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': [{'id': 'snap-123'}]}
        mock_get.return_value = mock_response

        result = self.client.list_snapshots('vm-123')
        self.assertEqual(result, [{'id': 'snap-123'}])

    @patch('vps.services.doprax_client.requests.post')
    def test_rebuild_vps(self, mock_post):
        """Test rebuilding VPS"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {'data': {'status': 'rebuilding'}}
        mock_post.return_value = mock_response

        result = self.client.rebuild_vps('vm-123', 'ubuntu-22-04')
        self.assertEqual(result, {'status': 'rebuilding'})


class VPSViewsTest(TestCase):
    """Test cases for VPS views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.plan = VPSPlan.objects.create(
            name='Test Plan',
            cpu_cores=2,
            ram_gb=4,
            disk_gb=50,
            bandwidth_gb=1000,
            price_per_month=Decimal('10.00')
        )
        self.vps = VPSInstance.objects.create(
            user=self.user,
            plan=self.plan,
            instance_id='test-instance-123',
            status='active',
            expires_at=timezone.now() + timedelta(days=30),
            ip_address='192.168.1.1'
        )
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.00'))

    def test_vps_dashboard_unauthenticated(self):
        """Test dashboard requires authentication"""
        response = self.client.get(reverse('vps:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_vps_dashboard_authenticated(self):
        """Test dashboard for authenticated user"""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('vps:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test-instance-123')

    @patch('vps.views.DopraxClient')
    def test_create_vps_success(self, mock_client):
        """Test successful VPS creation"""
        self.client.login(username='testuser', password='testpass')

        mock_client_instance = MagicMock()
        mock_client_instance.get_locations_and_plans.return_value = {
            'locationsList': [{'locationCode': 'us-east', 'provider': 'DigitalOcean'}]
        }
        mock_client_instance.create_vps.return_value = {'vmCode': 'vm-123', 'ipv4': '1.2.3.4'}
        mock_client.return_value = mock_client_instance

        data = {
            'plan': self.plan.id,
            'location': 'us-east',
            'operating_system': 'ubuntu-20-04',
            'vm_name': 'test-vm'
        }
        response = self.client.post(reverse('vps:create_vps'), data)
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard

        # Check VPS was created
        vps = VPSInstance.objects.get(instance_id='vm-123')
        self.assertEqual(vps.status, 'pending')

        # Check wallet was debited
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('90.00'))

    def test_create_vps_insufficient_balance(self):
        """Test VPS creation with insufficient balance"""
        self.wallet.balance = Decimal('5.00')
        self.wallet.save()
        self.client.login(username='testuser', password='testpass')

        data = {
            'plan': self.plan.id,
            'location': 'us-east',
            'operating_system': 'ubuntu-20-04'
        }
        response = self.client.post(reverse('vps:create_vps'), data)
        self.assertEqual(response.status_code, 200)  # Stay on form
        self.assertContains(response, 'Insufficient balance')

    @patch('vps.views.DopraxClient')
    def test_create_vps_api_error(self, mock_client):
        """Test VPS creation with API error"""
        self.client.login(username='testuser', password='testpass')

        mock_client_instance = MagicMock()
        mock_client_instance.create_vps.side_effect = DopraxAPIError("API Error")
        mock_client.return_value = mock_client_instance

        data = {
            'plan': self.plan.id,
            'location': 'us-east',
            'operating_system': 'ubuntu-20-04'
        }
        response = self.client.post(reverse('vps:create_vps'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Failed to create VPS')

    def test_vps_detail_unauthenticated(self):
        """Test VPS detail requires authentication"""
        response = self.client.get(reverse('vps:vps_detail', args=['test-instance-123']))
        self.assertEqual(response.status_code, 302)

    def test_vps_detail_not_found(self):
        """Test VPS detail for non-existent VPS"""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('vps:vps_detail', args=['non-existent']))
        self.assertEqual(response.status_code, 404)

    def test_vps_detail_wrong_user(self):
        """Test VPS detail for another user's VPS"""
        other_user = User.objects.create_user(username='other', password='pass')
        self.client.login(username='other', password='pass')
        response = self.client.get(reverse('vps:vps_detail', args=['test-instance-123']))
        self.assertEqual(response.status_code, 404)

    @patch('vps.views.DopraxClient')
    def test_vps_detail_success(self, mock_client):
        """Test successful VPS detail view"""
        self.client.login(username='testuser', password='testpass')

        mock_client_instance = MagicMock()
        mock_client_instance.get_vps_status.return_value = {
            'status': 'running',
            'ipv4': '1.2.3.5'
        }
        mock_client.return_value = mock_client_instance

        response = self.client.get(reverse('vps:vps_detail', args=['test-instance-123']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test-instance-123')

        # Check status was updated
        self.vps.refresh_from_db()
        self.assertEqual(self.vps.status, 'running')
        self.assertEqual(self.vps.ip_address, '1.2.3.5')

    @patch('vps.views.DopraxClient')
    def test_vps_action_start(self, mock_client):
        """Test VPS start action"""
        self.client.login(username='testuser', password='testpass')

        mock_client_instance = MagicMock()
        mock_client_instance.execute_vps_command.return_value = {'msg': 'success'}
        mock_client.return_value = mock_client_instance

        data = {'action': 'start'}
        response = self.client.post(
            reverse('vps:vps_action', args=['test-instance-123']),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])

        # Check status was updated
        self.vps.refresh_from_db()
        self.assertEqual(self.vps.status, 'active')

    @patch('vps.views.DopraxClient')
    def test_vps_action_api_error(self, mock_client):
        """Test VPS action with API error"""
        self.client.login(username='testuser', password='testpass')

        mock_client_instance = MagicMock()
        mock_client_instance.execute_vps_command.side_effect = DopraxAPIError("API Error")
        mock_client.return_value = mock_client_instance

        data = {'action': 'start'}
        response = self.client.post(
            reverse('vps:vps_action', args=['test-instance-123']),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])

    def test_vps_plans_view(self):
        """Test VPS plans view"""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('vps:vps_plans'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Plan')

    @patch('vps.views.DopraxClient')
    def test_start_vps_ajax(self, mock_client):
        """Test start VPS via AJAX"""
        self.client.login(username='testuser', password='testpass')

        mock_client_instance = MagicMock()
        mock_client_instance.execute_vps_command.return_value = {'msg': 'success'}
        mock_client.return_value = mock_client_instance

        response = self.client.post(reverse('vps:start_vps', args=['test-instance-123']))
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['status'], 'active')

    @patch('vps.views.DopraxClient')
    def test_stop_vps_ajax(self, mock_client):
        """Test stop VPS via AJAX"""
        self.client.login(username='testuser', password='testpass')

        mock_client_instance = MagicMock()
        mock_client_instance.execute_vps_command.return_value = {'msg': 'success'}
        mock_client.return_value = mock_client_instance

        response = self.client.post(reverse('vps:stop_vps', args=['test-instance-123']))
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['status'], 'stopped')

    @patch('vps.views.DopraxClient')
    def test_vps_monitoring(self, mock_client):
        """Test VPS monitoring view"""
        self.client.login(username='testuser', password='testpass')

        mock_client_instance = MagicMock()
        mock_client_instance.get_vps_status.return_value = {'status': 'active'}
        mock_client_instance.get_vps_network_info.return_value = {'ip': '1.2.3.4'}
        mock_client_instance.get_vps_traffic.return_value = {'traffic': '100GB'}
        mock_client.return_value = mock_client_instance

        response = self.client.get(reverse('vps:vps_monitoring', args=['test-instance-123']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test-instance-123')


class ManagementCommandsTest(TestCase):
    """Test cases for management commands"""

    @patch('vps.management.commands.sync_plans.DopraxClient')
    def test_sync_plans_command(self, mock_client):
        """Test sync_plans management command"""
        mock_client_instance = MagicMock()
        mock_client_instance.get_locations_and_plans.return_value = {
            'locationsList': [
                {
                    'locationCode': 'us-east',
                    'name': 'US East',
                    'provider': 'DigitalOcean'
                }
            ],
            'locationMachineTypeMapping': {
                'us-east': [
                    {
                        'name': '2CPU-4GB',
                        'cpu': 2,
                        'ramGb': 4,
                        'ssdGb': 50,
                        'monthlyTrafficGb': 1000,
                        'monthlyPriceUsd': 10.0
                    }
                ]
            }
        }
        mock_client.return_value = mock_client_instance

        call_command('sync_plans')

        # Check plan was created
        plan = VPSPlan.objects.get(name='2CPU-4GB')
        self.assertEqual(plan.cpu_cores, 2)
        self.assertEqual(plan.ram_gb, 4)

    @patch('vps.management.commands.sync_plans.DopraxClient')
    def test_sync_plans_dry_run(self, mock_client):
        """Test sync_plans with dry run"""
        mock_client_instance = MagicMock()
        mock_client_instance.get_locations_and_plans.return_value = {
            'locationsList': [],
            'locationMachineTypeMapping': {}
        }
        mock_client.return_value = mock_client_instance

        call_command('sync_plans', '--dry-run')

        # No plans should be created
        self.assertEqual(VPSPlan.objects.count(), 0)

    @patch('vps.management.commands.update_vps_statuses.DopraxClient')
    def test_update_vps_statuses_command(self, mock_client):
        """Test update_vps_statuses management command"""
        user = User.objects.create_user(username='testuser', password='testpass')
        plan = VPSPlan.objects.create(
            name='Test Plan',
            cpu_cores=2,
            ram_gb=4,
            disk_gb=50,
            bandwidth_gb=1000,
            price_per_month=Decimal('10.00')
        )
        vps = VPSInstance.objects.create(
            user=user,
            plan=plan,
            instance_id='test-vm-123',
            status='pending',
            expires_at=timezone.now() + timedelta(days=30)
        )

        mock_client_instance = MagicMock()
        mock_client_instance.get_vps_status.return_value = {
            'status': 'running',
            'ipv4': '1.2.3.4'
        }
        mock_client.return_value = mock_client_instance

        call_command('update_vps_statuses')

        # Check status was updated
        vps.refresh_from_db()
        self.assertEqual(vps.status, 'active')
        self.assertEqual(vps.ip_address, '1.2.3.4')

    @patch('vps.management.commands.update_vps_statuses.DopraxClient')
    def test_update_vps_statuses_dry_run(self, mock_client):
        """Test update_vps_statuses with dry run"""
        user = User.objects.create_user(username='testuser', password='testpass')
        plan = VPSPlan.objects.create(
            name='Test Plan',
            cpu_cores=2,
            ram_gb=4,
            disk_gb=50,
            bandwidth_gb=1000,
            price_per_month=Decimal('10.00')
        )
        vps = VPSInstance.objects.create(
            user=user,
            plan=plan,
            instance_id='test-vm-123',
            status='pending',
            expires_at=timezone.now() + timedelta(days=30)
        )

        mock_client_instance = MagicMock()
        mock_client_instance.get_vps_status.return_value = {
            'status': 'running',
            'ipv4': '1.2.3.4'
        }
        mock_client.return_value = mock_client_instance

        call_command('update_vps_statuses', '--dry-run')

        # Status should not change in dry run
        vps.refresh_from_db()
        self.assertEqual(vps.status, 'pending')
        self.assertIsNone(vps.ip_address)

    @patch('vps.management.commands.update_vps_statuses.DopraxClient')
    def test_update_vps_statuses_api_error(self, mock_client):
        """Test update_vps_statuses with API error"""
        user = User.objects.create_user(username='testuser', password='testpass')
        plan = VPSPlan.objects.create(
            name='Test Plan',
            cpu_cores=2,
            ram_gb=4,
            disk_gb=50,
            bandwidth_gb=1000,
            price_per_month=Decimal('10.00')
        )
        VPSInstance.objects.create(
            user=user,
            plan=plan,
            instance_id='test-vm-123',
            status='pending',
            expires_at=timezone.now() + timedelta(days=30)
        )

        mock_client_instance = MagicMock()
        mock_client_instance.get_vps_status.side_effect = DopraxAPIError("API Error")
        mock_client.return_value = mock_client_instance

        call_command('update_vps_statuses')

        # Status should remain unchanged
        vps = VPSInstance.objects.get(instance_id='test-vm-123')
        self.assertEqual(vps.status, 'pending')
