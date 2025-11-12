from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Create your models here.

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')

    def __str__(self):
        return f"{self.user.username}'s Wallet"

    def deposit(self, amount, description=''):
        """Deposit amount to wallet balance"""
        if amount <= 0:
            raise ValidationError("Deposit amount must be positive")
        self.balance += amount
        self.save()
        Transaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type='deposit',
            description=description,
            status='completed'
        )

    def withdraw(self, amount, description=''):
        """Withdraw amount from wallet balance"""
        if amount <= 0:
            raise ValidationError("Withdrawal amount must be positive")
        if self.balance < amount:
            raise ValidationError("Insufficient balance")
        self.balance -= amount
        self.save()
        Transaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type='withdraw',
            description=description,
            status='completed'
        )

    def get_transaction_history(self):
        """Get all transactions for this wallet"""
        return self.transaction_set.all().order_by('-timestamp')

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdraw', 'Withdraw'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reference_id = models.CharField(max_length=100, blank=True, null=True)  # For payment gateway reference

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.status})"

    @staticmethod
    def create_transaction(wallet, amount, transaction_type, description='', status='pending', reference_id=None):
        """Static method to create a transaction"""
        return Transaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            status=status,
            reference_id=reference_id
        )
