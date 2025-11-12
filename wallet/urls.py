from django.urls import path
from . import views

app_name = 'wallet'

urlpatterns = [
    path('dashboard/', views.wallet_dashboard, name='wallet_dashboard'),
    path('history/', views.transaction_history, name='transaction_history'),
    path('deposit/', views.initiate_deposit, name='initiate_deposit'),
    path('withdraw/', views.request_withdrawal, name='request_withdrawal'),
    path('verify/', views.verify_payment, name='verify_payment'),
    path('webhook/', views.payment_webhook, name='payment_webhook'),
]