from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
import json

from accounts.models import User
from wallet.models import Wallet, Transaction
from vps.models import VPSInstance
from billing.models import BillingCycle, Invoice


@login_required
def dashboard(request):
    """Main dashboard view combining all user data"""
    user = request.user

    # Get wallet information
    try:
        wallet = Wallet.objects.get(user=user)
        wallet_balance = wallet.balance
    except Wallet.DoesNotExist:
        wallet_balance = 0

    # Get recent transactions (last 5)
    recent_transactions = Transaction.objects.filter(
        wallet__user=user
    ).order_by('-timestamp')[:5]

    # Get VPS instances
    vps_instances = VPSInstance.objects.filter(user=user)
    active_vps_count = vps_instances.filter(status='active').count()
    total_vps_count = vps_instances.count()

    # Get recent VPS instances (last 3)
    recent_vps = vps_instances.order_by('-created_at')[:3]

    # Get billing information
    current_billing_cycle = BillingCycle.objects.filter(
        user=user,
        status='active'
    ).first()

    # Calculate total monthly cost
    monthly_cost = 0
    if current_billing_cycle:
        monthly_cost = current_billing_cycle.total_amount

    # Get recent invoices (last 3)
    recent_invoices = Invoice.objects.filter(
        user=user
    ).order_by('-issued_date')[:3]

    # Get pending invoices count
    pending_invoices_count = Invoice.objects.filter(
        user=user,
        status='unpaid'
    ).count()

    # Get upcoming expirations (next 7 days)
    upcoming_expirations = vps_instances.filter(
        expires_at__lte=timezone.now() + timedelta(days=7),
        expires_at__gte=timezone.now(),
        status='active'
    ).count()

    # Get low balance warning
    low_balance_warning = wallet_balance < monthly_cost and monthly_cost > 0

    context = {
        'wallet_balance': wallet_balance,
        'recent_transactions': recent_transactions,
        'active_vps_count': active_vps_count,
        'total_vps_count': total_vps_count,
        'recent_vps': recent_vps,
        'monthly_cost': monthly_cost,
        'recent_invoices': recent_invoices,
        'pending_invoices_count': pending_invoices_count,
        'upcoming_expirations': upcoming_expirations,
        'low_balance_warning': low_balance_warning,
        'current_billing_cycle': current_billing_cycle,
    }

    return render(request, 'dashboard/dashboard.html', context)


@login_required
def profile(request):
    """User profile management"""
    if request.method == 'POST':
        # Handle profile update
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', getattr(user, 'phone', ''))
        user.save()

        messages.success(request, 'پروفایل با موفقیت بروزرسانی شد.')
        return redirect('dashboard:profile')

    return render(request, 'dashboard/profile.html')


@login_required
def settings(request):
    """User account settings"""
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'change_password':
            # Handle password change
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if not request.user.check_password(current_password):
                messages.error(request, 'رمز عبور فعلی اشتباه است.')
            elif new_password != confirm_password:
                messages.error(request, 'رمز عبور جدید و تکرار آن مطابقت ندارند.')
            elif len(new_password) < 8:
                messages.error(request, 'رمز عبور باید حداقل ۸ کاراکتر باشد.')
            else:
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, 'رمز عبور با موفقیت تغییر یافت.')
                return redirect('accounts:login')

        elif action == 'update_notifications':
            # Handle notification preferences
            messages.success(request, 'تنظیمات اعلان‌ها بروزرسانی شد.')

        return redirect('dashboard:settings')

    return render(request, 'dashboard/settings.html')


@login_required
def notifications(request):
    """User notifications"""
    # For now, return empty notifications
    # In a real implementation, you'd have a Notification model
    notifications_list = []

    context = {
        'notifications': notifications_list,
    }

    return render(request, 'dashboard/notifications.html', context)
