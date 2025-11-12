import requests
from django.conf import settings
from .models import Transaction
import os

class ZarinpalPaymentGateway:
    """Zarinpal payment gateway integration"""

    def __init__(self):
        self.merchant_id = os.environ.get('ZARINPAL_MERCHANT_ID', 'test')  # Use test for development
        self.callback_url = os.environ.get('ZARINPAL_CALLBACK_URL', 'http://localhost:8000/wallet/verify/')
        self.api_url = 'https://api.zarinpal.com/pg/v4/payment/request.json'
        self.verify_url = 'https://api.zarinpal.com/pg/v4/payment/verify.json'

    def initiate_payment(self, amount, description='', email='', mobile=''):
        """Initiate a payment request to Zarinpal"""
        payload = {
            'merchant_id': self.merchant_id,
            'amount': int(amount * 10),  # Convert to Rials (assuming amount is in Toman)
            'description': description or 'Wallet Deposit',
            'callback_url': self.callback_url,
            'metadata': {
                'email': email,
                'mobile': mobile,
            }
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('data') and data['data'].get('code') == 100:
                return {
                    'success': True,
                    'authority': data['data']['authority'],
                    'payment_url': f"https://www.zarinpal.com/pg/StartPay/{data['data']['authority']}"
                }
            else:
                return {
                    'success': False,
                    'error': data.get('errors', {}).get('code', 'Unknown error')
                }
        except requests.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }

    def verify_payment(self, authority, amount):
        """Verify payment with Zarinpal"""
        payload = {
            'merchant_id': self.merchant_id,
            'authority': authority,
            'amount': int(amount * 10),  # Convert to Rials
        }

        try:
            response = requests.post(self.verify_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('data') and data['data'].get('code') == 100:
                return {
                    'success': True,
                    'ref_id': data['data']['ref_id'],
                    'card_pan': data['data'].get('card_pan'),
                    'card_hash': data['data'].get('card_hash'),
                }
            else:
                return {
                    'success': False,
                    'error': data.get('errors', {}).get('code', 'Payment not verified')
                }
        except requests.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
zarinpal_gateway = ZarinpalPaymentGateway()