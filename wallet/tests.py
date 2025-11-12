from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.http import JsonResponse
from decimal import Decimal
from unittest.mock import patch, MagicMock
import json
from .models import Wallet, Transaction
from .forms import DepositForm, WithdrawalForm
from .payment_gateway import ZarinpalPaymentGateway


class WalletModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.wallet = Wallet.objects.create(user=self.user, balance=100.00)

    def test_wallet_creation(self):
        self.assertEqual(self.wallet.user.username, 'testuser')
        self.assertEqual(self.wallet.balance, Decimal('100.00'))
        self.assertEqual(self.wallet.currency, 'USD')

    def test_wallet_str(self):
        self.assertEqual(str(self.wallet), "testuser's Wallet")

    def test_deposit_positive_amount(self):
        self.wallet.deposit(50.00, 'Test deposit')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('150.00'))
        transaction = Transaction.objects.get(wallet=self.wallet)
        self.assertEqual(transaction.amount, Decimal('50.00'))
        self.assertEqual(transaction.transaction_type, 'deposit')
        self.assertEqual(transaction.status, 'completed')

    def test_deposit_zero_amount(self):
        with self.assertRaises(ValidationError):
            self.wallet.deposit(0.00)

    def test_deposit_negative_amount(self):
        with self.assertRaises(ValidationError):
            self.wallet.deposit(-10.00)

    def test_withdraw_positive_amount(self):
        self.wallet.withdraw(50.00, 'Test withdraw')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('50.00'))
        transaction = Transaction.objects.get(wallet=self.wallet)
        self.assertEqual(transaction.amount, Decimal('50.00'))
        self.assertEqual(transaction.transaction_type, 'withdraw')

    def test_withdraw_zero_amount(self):
        with self.assertRaises(ValidationError):
            self.wallet.withdraw(0.00)

    def test_withdraw_negative_amount(self):
        with self.assertRaises(ValidationError):
            self.wallet.withdraw(-10.00)

    def test_withdraw_insufficient_balance(self):
        with self.assertRaises(ValidationError):
            self.wallet.withdraw(200.00)

    def test_get_transaction_history(self):
        self.wallet.deposit(20.00)
        self.wallet.withdraw(10.00)
        history = self.wallet.get_transaction_history()
        self.assertEqual(history.count(), 2)
        # Check ordering (most recent first)
        self.assertEqual(history.first().transaction_type, 'withdraw')


class TransactionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.wallet = Wallet.objects.create(user=self.user)

    def test_transaction_creation(self):
        transaction = Transaction.objects.create(
            wallet=self.wallet,
            amount=100.00,
            transaction_type='deposit',
            status='completed'
        )
        self.assertEqual(transaction.amount, Decimal('100.00'))
        self.assertEqual(transaction.transaction_type, 'deposit')
        self.assertEqual(transaction.status, 'completed')

    def test_transaction_str(self):
        transaction = Transaction.objects.create(
            wallet=self.wallet,
            amount=50.00,
            transaction_type='withdraw',
            status='pending'
        )
        self.assertEqual(str(transaction), "withdraw - 50.0 (pending)")

    def test_create_transaction_static_method(self):
        transaction = Transaction.create_transaction(
            wallet=self.wallet,
            amount=75.00,
            transaction_type='payment',
            description='Test payment',
            status='completed',
            reference_id='ref123'
        )
        self.assertEqual(transaction.amount, Decimal('75.00'))
        self.assertEqual(transaction.transaction_type, 'payment')
        self.assertEqual(transaction.description, 'Test payment')
        self.assertEqual(transaction.reference_id, 'ref123')

    def test_transaction_invalid_type(self):
        with self.assertRaises(ValidationError):
            Transaction.objects.create(
                wallet=self.wallet,
                amount=10.00,
                transaction_type='invalid',
                status='completed'
            )

    def test_transaction_invalid_status(self):
        with self.assertRaises(ValidationError):
            Transaction.objects.create(
                wallet=self.wallet,
                amount=10.00,
                transaction_type='deposit',
                status='invalid'
            )


class WalletFormTest(TestCase):
    def test_deposit_form_valid(self):
        form_data = {'amount': '50.00', 'description': 'Test deposit'}
        form = DepositForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['amount'], Decimal('50.00'))
        self.assertEqual(form.cleaned_data['description'], 'Test deposit')

    def test_deposit_form_invalid_amount_zero(self):
        form_data = {'amount': '0.00'}
        form = DepositForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_deposit_form_invalid_amount_negative(self):
        form_data = {'amount': '-10.00'}
        form = DepositForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

    def test_deposit_form_no_description(self):
        form_data = {'amount': '25.00'}
        form = DepositForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['description'], '')

    def test_withdrawal_form_valid(self):
        form_data = {'amount': '30.00', 'description': 'Test withdrawal'}
        form = WithdrawalForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['amount'], Decimal('30.00'))

    def test_withdrawal_form_invalid_amount(self):
        form_data = {'amount': '0.00'}
        form = WithdrawalForm(data=form_data)
        self.assertFalse(form.is_valid())


class PaymentGatewayTest(TestCase):
    def setUp(self):
        self.gateway = ZarinpalPaymentGateway()

    @patch('wallet.payment_gateway.requests.post')
    def test_initiate_payment_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {'code': 100, 'authority': 'AUTH123'},
            'errors': {}
        }
        mock_post.return_value = mock_response

        result = self.gateway.initiate_payment(100.00, 'Test payment', 'test@example.com')
        self.assertTrue(result['success'])
        self.assertEqual(result['authority'], 'AUTH123')
        self.assertIn('payment_url', result)

    @patch('wallet.payment_gateway.requests.post')
    def test_initiate_payment_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {'data': None, 'errors': {'code': 'Invalid'}}
        mock_post.return_value = mock_response

        result = self.gateway.initiate_payment(100.00)
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Invalid')

    @patch('wallet.payment_gateway.requests.post')
    def test_verify_payment_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {'code': 100, 'ref_id': 'REF123', 'card_pan': '1234', 'card_hash': 'HASH'}
        }
        mock_post.return_value = mock_response

        result = self.gateway.verify_payment('AUTH123', 100.00)
        self.assertTrue(result['success'])
        self.assertEqual(result['ref_id'], 'REF123')

    @patch('wallet.payment_gateway.requests.post')
    def test_verify_payment_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {'data': None, 'errors': {'code': 'NotVerified'}}
        mock_post.return_value = mock_response

        result = self.gateway.verify_payment('AUTH123', 100.00)
        self.assertFalse(result['success'])


class WalletViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.wallet = Wallet.objects.create(user=self.user, balance=100.00)
        self.client.login(username='testuser', password='testpass')

    def test_wallet_dashboard_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse('wallet:wallet_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_wallet_dashboard_authenticated(self):
        response = self.client.get(reverse('wallet:wallet_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wallet/dashboard.html')
        self.assertIn('wallet', response.context)
        self.assertIn('transactions', response.context)

    def test_transaction_history(self):
        response = self.client.get(reverse('wallet:transaction_history'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wallet/history.html')

    @patch('wallet.views.zarinpal_gateway')
    def test_initiate_deposit_success(self, mock_gateway):
        mock_gateway.initiate_payment.return_value = {
            'success': True,
            'authority': 'AUTH123',
            'payment_url': 'https://zarinpal.com/pay/AUTH123'
        }
        response = self.client.post(reverse('wallet:initiate_deposit'), {'amount': '50.00', 'description': 'Test'})
        self.assertEqual(response.status_code, 302)  # Redirect to payment
        transaction = Transaction.objects.get(wallet=self.wallet)
        self.assertEqual(transaction.status, 'pending')
        self.assertEqual(transaction.reference_id, 'AUTH123')

    @patch('wallet.views.zarinpal_gateway')
    def test_initiate_deposit_failure(self, mock_gateway):
        mock_gateway.initiate_payment.return_value = {'success': False, 'error': 'Gateway error'}
        response = self.client.post(reverse('wallet:initiate_deposit'), {'amount': '50.00'})
        self.assertEqual(response.status_code, 302)  # Redirect back
        transaction = Transaction.objects.get(wallet=self.wallet)
        self.assertEqual(transaction.status, 'failed')

    def test_initiate_deposit_invalid_form(self):
        response = self.client.post(reverse('wallet:initiate_deposit'), {'amount': '0.00'})
        self.assertEqual(response.status_code, 302)  # Redirect back

    def test_request_withdrawal_success(self):
        response = self.client.post(reverse('wallet:request_withdrawal'), {'amount': '50.00', 'description': 'Test'})
        self.assertEqual(response.status_code, 302)
        transaction = Transaction.objects.get(wallet=self.wallet)
        self.assertEqual(transaction.transaction_type, 'withdraw')
        self.assertEqual(transaction.status, 'pending')

    def test_request_withdrawal_insufficient_balance(self):
        response = self.client.post(reverse('wallet:request_withdrawal'), {'amount': '200.00'})
        self.assertEqual(response.status_code, 302)
        # No transaction created

    @patch('wallet.views.zarinpal_gateway')
    def test_verify_payment_success(self, mock_gateway):
        transaction = Transaction.objects.create(
            wallet=self.wallet,
            amount=50.00,
            transaction_type='deposit',
            status='pending',
            reference_id='AUTH123'
        )
        mock_gateway.verify_payment.return_value = {'success': True, 'ref_id': 'REF123'}
        response = self.client.get(reverse('wallet:verify_payment'), {'Authority': 'AUTH123', 'Status': 'OK'})
        self.assertEqual(response.status_code, 302)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'completed')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('150.00'))

    @patch('wallet.views.zarinpal_gateway')
    def test_verify_payment_failure(self, mock_gateway):
        transaction = Transaction.objects.create(
            wallet=self.wallet,
            amount=50.00,
            transaction_type='deposit',
            status='pending',
            reference_id='AUTH123'
        )
        mock_gateway.verify_payment.return_value = {'success': False, 'error': 'Verification failed'}
        response = self.client.get(reverse('wallet:verify_payment'), {'Authority': 'AUTH123', 'Status': 'OK'})
        self.assertEqual(response.status_code, 302)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'failed')

    def test_verify_payment_cancelled(self):
        transaction = Transaction.objects.create(
            wallet=self.wallet,
            amount=50.00,
            transaction_type='deposit',
            status='pending',
            reference_id='AUTH123'
        )
        response = self.client.get(reverse('wallet:verify_payment'), {'Authority': 'AUTH123', 'Status': 'NOK'})
        self.assertEqual(response.status_code, 302)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'cancelled')

    def test_payment_webhook_success(self):
        transaction = Transaction.objects.create(
            wallet=self.wallet,
            amount=50.00,
            transaction_type='deposit',
            status='pending',
            reference_id='REF123'
        )
        data = {'reference_id': 'REF123', 'status': 'success'}
        response = self.client.post(
            reverse('wallet:payment_webhook'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'completed')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('150.00'))

    def test_payment_webhook_failure(self):
        transaction = Transaction.objects.create(
            wallet=self.wallet,
            amount=50.00,
            transaction_type='deposit',
            status='pending',
            reference_id='REF123'
        )
        data = {'reference_id': 'REF123', 'status': 'failed'}
        response = self.client.post(
            reverse('wallet:payment_webhook'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'failed')

    def test_payment_webhook_invalid_json(self):
        response = self.client.post(
            reverse('wallet:payment_webhook'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_payment_webhook_transaction_not_found(self):
        data = {'reference_id': 'NONEXISTENT', 'status': 'success'}
        response = self.client.post(
            reverse('wallet:payment_webhook'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
