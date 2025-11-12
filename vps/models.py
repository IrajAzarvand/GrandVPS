from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class VPSPlan(models.Model):
    name = models.CharField(max_length=100)
    cpu_cores = models.IntegerField()
    ram_gb = models.IntegerField()
    disk_gb = models.IntegerField()
    bandwidth_gb = models.IntegerField()
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class VPSInstance(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('stopped', 'Stopped'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(VPSPlan, on_delete=models.CASCADE)
    instance_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} - {self.instance_id}"

    def renew(self, days=30):
        """Renew the VPS for specified days"""
        from django.utils import timezone
        from datetime import timedelta

        if self.expires_at < timezone.now():
            # If already expired, renew from now
            self.expires_at = timezone.now() + timedelta(days=days)
        else:
            # Extend current expiration
            self.expires_at += timedelta(days=days)
        self.save()
        return self.expires_at

    def is_expired(self):
        """Check if VPS is expired"""
        from django.utils import timezone
        return self.expires_at < timezone.now()

    def days_until_expiry(self):
        """Get days until expiry"""
        from django.utils import timezone
        if self.is_expired():
            return 0
        return (self.expires_at - timezone.now()).days
