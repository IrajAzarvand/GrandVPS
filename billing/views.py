from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db import models
from django.db.models import Sum
from .models import BillingCycle, Invoice
from .services import HourlyBillingService, NotificationService, AutoRenewalService

@login_required
def billing_dashboard(request):
    """Display user's billing dashboard"""
    user = request.user

    # Get billing cycles
    billing_cycles = BillingCycle.objects.filter(user=user).order_by('-created_at')[:10]

    # Get invoices
    invoices = Invoice.objects.filter(user=user).order_by('-issued_date')[:10]

    # Get current wallet balance
    wallet = user.wallet

    # Check renewal status
    renewal_check = NotificationService.check_wallet_balance_for_renewal(user)

    context = {
        'billing_cycles': billing_cycles,
        'invoices': invoices,
        'wallet_balance': wallet.balance,
        'renewal_check': renewal_check,
    }

    return render(request, 'billing/dashboard.html', context)

@login_required
def invoice_detail(request, invoice_id):
    """Display invoice details"""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice})

@login_required
def download_invoice(request, invoice_id):
    """Download invoice PDF"""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)

    if not invoice.pdf_file:
        from .services import InvoiceService
        pdf_buffer = InvoiceService.generate_invoice_pdf(invoice)
        invoice.pdf_file.save(f'invoice_{invoice.invoice_number}.pdf', pdf_buffer, save=True)

    response = HttpResponse(invoice.pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    return response

@login_required
def billing_history(request):
    """Display billing history"""
    user = request.user

    # Get all invoices
    invoices = Invoice.objects.filter(user=user).order_by('-issued_date')

    # Calculate statistics
    total_invoices = invoices.count()
    paid_invoices = invoices.filter(status='paid').count()
    pending_invoices = invoices.filter(status__in=['sent', 'unpaid']).count()

    # Calculate amounts
    paid_amount = invoices.filter(status='paid').aggregate(
        total=models.Sum('amount')
    )['total'] or 0

    pending_amount = invoices.filter(status__in=['sent', 'unpaid']).aggregate(
        total=models.Sum('amount')
    )['total'] or 0

    # Calculate average monthly (based on last 12 months)
    from django.utils import timezone
    from dateutil.relativedelta import relativedelta

    one_year_ago = timezone.now() - relativedelta(months=12)
    yearly_invoices = invoices.filter(issued_date__gte=one_year_ago)
    average_monthly = 0
    if yearly_invoices.exists():
        total_yearly = yearly_invoices.aggregate(total=models.Sum('amount'))['total'] or 0
        average_monthly = total_yearly / 12

    context = {
        'invoices': invoices,
        'total_invoices': total_invoices,
        'paid_invoices': paid_invoices,
        'pending_invoices': pending_invoices,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'average_monthly': average_monthly,
    }

    return render(request, 'billing/history.html', context)

@login_required
def billing_analytics(request):
    """Display billing analytics and statistics"""
    user = request.user

    # User-specific analytics
    total_billed = BillingCycle.objects.filter(user=user, status='paid').aggregate(
        total=models.Sum('amount')
    )['total'] or 0

    total_invoices = Invoice.objects.filter(user=user).count()
    paid_invoices = Invoice.objects.filter(user=user, status='paid').count()

    # Monthly spending trend (last 6 months)
    from django.db.models.functions import TruncMonth
    from django.utils import timezone
    from dateutil.relativedelta import relativedelta

    six_months_ago = timezone.now() - relativedelta(months=6)
    monthly_spending = BillingCycle.objects.filter(
        user=user,
        status='paid',
        paid_at__gte=six_months_ago
    ).annotate(
        month=TruncMonth('paid_at')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    context = {
        'total_billed': total_billed,
        'total_invoices': total_invoices,
        'paid_invoices': paid_invoices,
        'unpaid_invoices': total_invoices - paid_invoices,
        'monthly_spending': list(monthly_spending),
    }

    return render(request, 'billing/analytics.html', context)
