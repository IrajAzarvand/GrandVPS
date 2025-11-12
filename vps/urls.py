from django.urls import path
from . import views

app_name = 'vps'

urlpatterns = [
    path('', views.vps_dashboard, name='dashboard'),
    path('create/', views.create_vps, name='create'),
    path('plans/', views.vps_plans, name='plans'),
    path('<str:instance_id>/', views.vps_detail, name='detail'),
    path('<str:instance_id>/action/', views.vps_action, name='action'),
    path('<str:instance_id>/monitoring/', views.vps_monitoring, name='monitoring'),
    path('<str:instance_id>/start/', views.start_vps, name='start'),
    path('<str:instance_id>/stop/', views.stop_vps, name='stop'),
]