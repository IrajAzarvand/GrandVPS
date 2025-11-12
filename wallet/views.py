from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.http import HttpResponseForbidden
from .models import Wallet, Transaction
from .forms import DepositForm, WithdrawalForm
from .payment_gateway import zarinpal_gateway
import json
import time

def rate_limit(key_prefix, max_requests=5, window=60):
    """Simple rate limiting decorator"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                cache_key = f"{key_prefix}:{request.user.id}:{int(time.time() / window)}"
                requests = cache.get(cache_key, 0)
                if requests >= max_requests:
                    return HttpResponseForbidden("Rate limit exceeded. Please try again later.")
                cache.set(cache_key, requests + 1, window)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

@login_required
def wallet_dashboard(request):
    """View wallet balance and recent transactions"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.get_transaction_history()[:10]  # Last 10 transactions
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'deposit_form': DepositForm(),
        'withdrawal_form': WithdrawalForm(),
    }
    return render(request, 'wallet/dashboard.html', context)

@login_required
def transaction_history(request):
    """View full transaction history"""
    wallet = get_object_or_404(Wallet, user=request.user)
    transactions = wallet.get_transaction_history()
    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'wallet/history.html', context)

@login_required
@require_POST
@rate_limit('deposit', max_requests=3, window=300)  # 3 deposits per 5 minutes
def initiate_deposit(request):
    """Initiate a deposit via Zarinpal payment gateway"""
    form = DepositForm(request.POST)
    if form.is_valid():
        amount = form.cleaned_data['amount']
        description = form.cleaned_data['description']
        wallet = get_object_or_404(Wallet, user=request.user)

        # Create pending transaction
        transaction = Transaction.create_transaction(
            wallet=wallet,
            amount=amount,
            transaction_type='deposit',
            description=description,
            status='pending'
        )

        # Initiate payment with Zarinpal
        payment_result = zarinpal_gateway.initiate_payment(
            amount=amount,
            description=description or f"Wallet deposit - Transaction {transaction.id}",
            email=request.user.email,
            mobile=''  # Could add mobile field to user profile
        )

        if payment_result['success']:
            # Update transaction with authority
            transaction.reference_id = payment_result['authority']
            transaction.save()

            # Redirect to Zarinpal payment page
            return redirect(payment_result['payment_url'])
        else:
            # Payment initiation failed
            transaction.status = 'failed'
            transaction.save()
            messages.error(request, f"Payment initiation failed: {payment_result['error']}")
            return redirect('wallet:wallet_dashboard')

    messages.error(request, "Invalid deposit amount.")
    return redirect('wallet:wallet_dashboard')

@login_required
@require_POST
@rate_limit('withdrawal', max_requests=2, window=600)  # 2 withdrawals per 10 minutes
def request_withdrawal(request):
    """Request a withdrawal"""
    form = WithdrawalForm(request.POST)
    if form.is_valid():
        amount = form.cleaned_data['amount']
        description = form.cleaned_data['description']
        wallet = get_object_or_404(Wallet, user=request.user)

        try:
            # Check balance
            if wallet.balance < amount:
                messages.error(request, "Insufficient balance.")
                return redirect('wallet:wallet_dashboard')

            # Create pending withdrawal transaction
            transaction = Transaction.create_transaction(
                wallet=wallet,
                amount=amount,
                transaction_type='withdraw',
                description=description,
                status='pending'
            )

            messages.success(request, f"Withdrawal request of ${amount} submitted for approval. Transaction ID: {transaction.id}")
            return redirect('wallet:wallet_dashboard')

        except Exception as e:
            messages.error(request, f"Error processing withdrawal: {str(e)}")
            return redirect('wallet:wallet_dashboard')

    messages.error(request, "Invalid withdrawal amount.")
    return redirect('wallet:wallet_dashboard')

@login_required
def verify_payment(request):
    """Verify payment after returning from Zarinpal"""
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')

    if not authority:
        messages.error(request, "Invalid payment authority.")
        return redirect('wallet:wallet_dashboard')

    try:
        transaction = Transaction.objects.get(reference_id=authority, wallet__user=request.user)
    except Transaction.DoesNotExist:
        messages.error(request, "Transaction not found.")
        return redirect('wallet:wallet_dashboard')

    if status == 'OK':
        # Verify payment with Zarinpal
        verify_result = zarinpal_gateway.verify_payment(authority, transaction.amount)

        if verify_result['success']:
            # Payment successful
            transaction.status = 'completed'
            transaction.description += f" - Ref ID: {verify_result['ref_id']}"
            transaction.save()

            # Update wallet balance
            transaction.wallet.deposit(transaction.amount, f"Payment verified - Ref ID: {verify_result['ref_id']}")

            messages.success(request, f"Payment of ${transaction.amount} completed successfully!")
        else:
            # Payment verification failed
            transaction.status = 'failed'
            transaction.save()
            messages.error(request, f"Payment verification failed: {verify_result['error']}")
    else:
        # Payment was cancelled or failed
        transaction.status = 'cancelled'
        transaction.save()
        messages.warning(request, "Payment was cancelled.")

    return redirect('wallet:wallet_dashboard')

@csrf_exempt
@require_POST
def payment_webhook(request):
    """Handle payment gateway webhook callbacks"""
    try:
        data = json.loads(request.body)
        # TODO: Verify webhook authenticity
        # TODO: Update transaction status based on payment result
        reference_id = data.get('reference_id')
        status = data.get('status')  # 'success' or 'failed'

        if reference_id and status:
            try:
                transaction = Transaction.objects.get(reference_id=reference_id)
                if status == 'success':
                    transaction.status = 'completed'
                    transaction.wallet.deposit(transaction.amount, f"Payment confirmed - {reference_id}")
                else:
                    transaction.status = 'failed'
                transaction.save()
                return JsonResponse({'status': 'ok'})
            except Transaction.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Transaction not found'}, status=404)

        return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
