from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('dashboard/', views.billing_dashboard, name='dashboard'),
    path('history/', views.billing_history, name='history'),
    path('analytics/', views.billing_analytics, name='analytics'),
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoice/<int:invoice_id>/download/', views.download_invoice, name='download_invoice'),
]