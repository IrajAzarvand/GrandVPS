from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

# Create your models here.

class BillingCycle(models.Model):
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unpaid')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.start_date} to {self.end_date} - {self.amount}"

    @classmethod
    def create_billing_cycle(cls, user, start_date, end_date, amount):
        """Create a new billing cycle"""
        return cls.objects.create(
            user=user,
            start_date=start_date,
            end_date=end_date,
            amount=amount
        )

    def mark_as_paid(self):
        """Mark the billing cycle as paid"""
        from django.utils import timezone
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save()


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    billing_cycle = models.ForeignKey(BillingCycle, on_delete=models.CASCADE, blank=True, null=True)
    invoice_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    issued_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()
    pdf_file = models.FileField(upload_to='invoices/', blank=True, null=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.user.username} - {self.amount}"

    @classmethod
    def generate_invoice_number(cls):
        """Generate a unique invoice number"""
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        last_invoice = cls.objects.filter(invoice_number__startswith=date_str).order_by('-invoice_number').first()
        if last_invoice:
            num = int(last_invoice.invoice_number.split('-')[-1]) + 1
        else:
            num = 1
        return f"INV-{date_str}-{num:04d}"

    def calculate_hourly_cost(self, vps_instance):
        """Calculate hourly cost for a VPS instance with 10% profit margin"""
        monthly_cost = vps_instance.plan.price_per_month
        hourly_base = monthly_cost / Decimal('720')  # 30 days * 24 hours
        hourly_with_margin = hourly_base * Decimal('1.10')  # 10% profit margin
        return hourly_with_margin.quantize(Decimal('0.01'))

    def calculate_total_cost(self, vps_instances, hours):
        """Calculate total cost for multiple VPS instances over given hours"""
        total = Decimal('0')
        for instance in vps_instances:
            hourly_cost = self.calculate_hourly_cost(instance)
            total += hourly_cost * hours
        return total.quantize(Decimal('0.01'))
