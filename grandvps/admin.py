from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from django.shortcuts import render
from django.urls import path
from accounts.models import UserProfile
from wallet.models import Wallet, Transaction
from vps.models import VPSInstance, VPSPlan
from billing.models import BillingCycle, Invoice
import datetime


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'last_login')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login')
    search_fields = ('username', 'email', 'first_name', 'last_name')


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(VPSPlan)
class VPSPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'cpu_cores', 'ram_gb', 'disk_gb', 'bandwidth_gb', 'price_per_month', 'is_active')
    list_filter = ('is_active', 'cpu_cores', 'ram_gb')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(VPSInstance)
class VPSInstanceAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'plan', 'status', 'ip_address', 'expires_at', 'created_at')
    list_filter = ('status', 'plan', 'created_at', 'expires_at')
    search_fields = ('name', 'instance_id', 'user__username', 'ip_address')
    ordering = ('-created_at',)
    readonly_fields = ('instance_id', 'created_at', 'updated_at')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-updated_at',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'transaction_type', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('wallet__user__username', 'reference_id', 'description')
    ordering = ('-created_at',)


@admin.register(BillingCycle)
class BillingCycleAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_date', 'end_date', 'amount', 'status', 'paid_at')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('user__username',)
    ordering = ('-start_date',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'amount', 'status', 'due_date', 'issued_date')
    list_filter = ('status', 'issued_date', 'due_date')
    search_fields = ('invoice_number', 'user__username')
    ordering = ('-issued_date',)


class GrandVPSAdminSite(admin.AdminSite):
    site_header = 'GrandVPS Administration'
    site_title = 'GrandVPS Admin'
    index_title = 'Dashboard Overview'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('monitoring/', self.admin_view(self.monitoring_dashboard), name='monitoring_dashboard'),
        ]
        return custom_urls + urls

    def monitoring_dashboard(self, request):
        """Custom monitoring dashboard for administrators"""
        # Time range for analytics (last 30 days)
        thirty_days_ago = timezone.now() - datetime.timedelta(days=30)

        context = {
            'title': 'Monitoring Dashboard',
            # User statistics
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'new_users_30d': User.objects.filter(date_joined__gte=thirty_days_ago).count(),

            # VPS statistics
            'total_vps': VPSInstance.objects.count(),
            'active_vps': VPSInstance.objects.filter(status='active').count(),
            'pending_vps': VPSInstance.objects.filter(status='pending').count(),
            'suspended_vps': VPSInstance.objects.filter(status='suspended').count(),

            # Financial statistics
            'total_wallet_balance': Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0,
            'total_transactions': Transaction.objects.count(),
            'successful_transactions': Transaction.objects.filter(status='completed').count(),
            'pending_transactions': Transaction.objects.filter(status='pending').count(),

            # Billing statistics
            'total_invoices': Invoice.objects.count(),
            'paid_invoices': Invoice.objects.filter(status='paid').count(),
            'pending_invoices': Invoice.objects.filter(status__in=['sent', 'unpaid']).count(),
            'total_billed': Invoice.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0,

            # Recent activity
            'recent_users': User.objects.order_by('-date_joined')[:5],
            'recent_vps': VPSInstance.objects.order_by('-created_at')[:5],
            'recent_transactions': Transaction.objects.order_by('-created_at')[:10],
            'expiring_vps': VPSInstance.objects.filter(
                status='active',
                expires_at__lte=timezone.now() + datetime.timedelta(days=7)
            ).order_by('expires_at')[:10],

            # System health (basic)
            'low_balance_users': Wallet.objects.filter(balance__lt=10).count(),
            'old_pending_transactions': Transaction.objects.filter(
                status='pending',
                created_at__lt=timezone.now() - datetime.timedelta(hours=24)
            ).count(),
        }

        return render(request, 'admin/monitoring_dashboard.html', context)


# Create custom admin site
admin_site = GrandVPSAdminSite(name='grandvps_admin')
admin_site.register(User, CustomUserAdmin)
admin_site.register(VPSPlan, VPSPlanAdmin)
admin_site.register(VPSInstance, VPSInstanceAdmin)
admin_site.register(Wallet, WalletAdmin)
admin_site.register(Transaction, TransactionAdmin)
admin_site.register(BillingCycle, BillingCycleAdmin)
admin_site.register(Invoice, InvoiceAdmin)

# Replace default admin site
admin.site = admin_site