from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import VPSPlan, VPSInstance
from .forms import VPSCreationForm, VPSActionForm
from .services.doprax_client import DopraxClient, DopraxAPIError
from wallet.models import Wallet, Transaction
import logging

logger = logging.getLogger(__name__)


@login_required
def vps_dashboard(request):
    """Main VPS dashboard showing user's VPS instances"""
    vps_instances = VPSInstance.objects.filter(user=request.user).order_by('-created_at')

    # Calculate monthly cost
    monthly_cost = 0
    for vps in vps_instances.filter(status__in=['active', 'pending']):
        monthly_cost += vps.plan.price_per_month

    # Count expiring soon (next 7 days)
    expiring_soon_count = vps_instances.filter(
        expires_at__lte=timezone.now() + timedelta(days=7),
        expires_at__gte=timezone.now(),
        status='active'
    ).count()

    context = {
        'vps_instances': vps_instances,
        'total_vps': vps_instances.count(),
        'active_vps': vps_instances.filter(status='active').count(),
        'monthly_cost': monthly_cost,
        'expiring_soon_count': expiring_soon_count,
    }
    return render(request, 'vps/dashboard.html', context)


@login_required
def create_vps(request):
    """VPS creation form and processing"""
    if request.method == 'POST':
        form = VPSCreationForm(request.POST)
        if form.is_valid():
            try:
                # Get form data
                plan = form.cleaned_data['plan']
                location = form.cleaned_data['location']
                os_slug = form.cleaned_data['operating_system']
                vm_name = form.cleaned_data['vm_name']

                # Check wallet balance
                wallet = Wallet.objects.get(user=request.user)
                if wallet.balance < plan.price_per_month:
                    messages.error(request, f'Insufficient balance. Required: ${plan.price_per_month}, Available: ${wallet.balance}')
                    return redirect('vps:create_vps')

                # Get location details for provider info
                client = DopraxClient()
                locations_data = client.get_locations_and_plans()
                location_info = next(
                    (loc for loc in locations_data.get('locationsList', []) if loc['locationCode'] == location),
                    {}
                )
                provider_name = location_info.get('provider', 'Unknown')

                # Get machine code from plan (this is a simplification - in real implementation,
                # you'd need to map plan to machine code properly)
                machine_code = f"{plan.cpu_cores}cpu-{plan.ram_gb}gb-{plan.disk_gb}gb"

                # Create VPS via API
                vps_data = client.create_vps(
                    location_code=location,
                    machine_type_code=machine_code,
                    os_slug=os_slug,
                    provider_name=provider_name,
                    vm_name=vm_name
                )

                # Calculate expiration (30 days from now)
                expires_at = timezone.now() + timedelta(days=30)

                # Create VPS instance in database
                vps_instance = VPSInstance.objects.create(
                    user=request.user,
                    plan=plan,
                    instance_id=vps_data.get('vmCode', f'vps-{vm_name}'),
                    status='pending',
                    expires_at=expires_at,
                    ip_address=vps_data.get('ipv4')
                )

                # Deduct from wallet and create transaction
                wallet.balance -= plan.price_per_month
                wallet.save()

                Transaction.objects.create(
                    wallet=wallet,
                    amount=-plan.price_per_month,
                    transaction_type='vps_purchase',
                    description=f'VPS Creation: {plan.name}',
                    reference_id=vps_instance.instance_id
                )

                messages.success(request, f'VPS "{vm_name}" created successfully! Instance ID: {vps_instance.instance_id}')
                return redirect('vps:dashboard')

            except DopraxAPIError as e:
                logger.error(f'VPS creation API error: {str(e)}')
                messages.error(request, f'Failed to create VPS: {str(e)}')
            except Exception as e:
                logger.error(f'VPS creation error: {str(e)}')
                messages.error(request, 'An unexpected error occurred. Please try again.')
    else:
        form = VPSCreationForm()

    context = {
        'form': form,
        'plans': VPSPlan.objects.filter(is_active=True),
    }
    return render(request, 'vps/create.html', context)


@login_required
def vps_detail(request, instance_id):
    """Detailed view of a specific VPS instance"""
    vps = get_object_or_404(VPSInstance, instance_id=instance_id, user=request.user)

    context = {
        'vps': vps,
        'action_form': VPSActionForm(vps),
    }
    return render(request, 'vps/detail.html', context)


@login_required
@require_POST
def vps_action(request, instance_id):
    """Handle VPS actions (start, stop, restart)"""
    vps = get_object_or_404(VPSInstance, instance_id=instance_id, user=request.user)

    form = VPSActionForm(request.POST, vps_instance=vps)
    if form.is_valid():
        action = form.cleaned_data['action']

        try:
            client = DopraxClient()

            # Map action to API command
            command_mapping = {
                'start': 'turnon',
                'stop': 'shutdown',
                'restart': 'reboot'
            }

            api_command = command_mapping[action]
            result = client.execute_vps_command(vps.instance_id, api_command)

            # Update status based on action
            if action == 'start':
                vps.status = 'active'
            elif action == 'stop':
                vps.status = 'stopped'
            # For restart, status might remain the same or change temporarily

            vps.save()

            messages.success(request, f'VPS {action} command executed successfully')
            return JsonResponse({'success': True, 'message': f'VPS {action} successful'})

        except DopraxAPIError as e:
            logger.error(f'VPS action error: {str(e)}')
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            logger.error(f'Unexpected VPS action error: {str(e)}')
            return JsonResponse({'success': False, 'message': 'An unexpected error occurred'}, status=500)
    else:
        return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)


@login_required
def vps_plans(request):
    """Display available VPS plans"""
    plans = VPSPlan.objects.filter(is_active=True).order_by('price_per_month')
    context = {
        'plans': plans,
    }
    return render(request, 'vps/plans.html', context)


@login_required
@require_POST
def start_vps(request, instance_id):
    """Start a VPS instance via AJAX"""
    vps = get_object_or_404(VPSInstance, instance_id=instance_id, user=request.user)

    try:
        client = DopraxClient()
        result = client.execute_vps_command(vps.instance_id, 'turnon')

        # Update status
        vps.status = 'active'
        vps.save()

        return JsonResponse({
            'success': True,
            'message': 'VPS started successfully',
            'status': 'active'
        })

    except DopraxAPIError as e:
        logger.error(f'VPS start error: {str(e)}')
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        logger.error(f'Unexpected VPS start error: {str(e)}')
        return JsonResponse({'success': False, 'message': 'An unexpected error occurred'}, status=500)


@login_required
@require_POST
def stop_vps(request, instance_id):
    """Stop a VPS instance via AJAX"""
    vps = get_object_or_404(VPSInstance, instance_id=instance_id, user=request.user)

    try:
        client = DopraxClient()
        result = client.execute_vps_command(vps.instance_id, 'shutdown')

        # Update status
        vps.status = 'stopped'
        vps.save()

        return JsonResponse({
            'success': True,
            'message': 'VPS stopped successfully',
            'status': 'stopped'
        })

    except DopraxAPIError as e:
        logger.error(f'VPS stop error: {str(e)}')
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        logger.error(f'Unexpected VPS stop error: {str(e)}')
        return JsonResponse({'success': False, 'message': 'An unexpected error occurred'}, status=500)


@login_required
def vps_monitoring(request, instance_id):
    """VPS monitoring and resource information"""
    vps = get_object_or_404(VPSInstance, instance_id=instance_id, user=request.user)

    monitoring_data = {}

    try:
        client = DopraxClient()

        # Get VPS details
        vps_data = client.get_vps_status(vps.instance_id)
        monitoring_data['status'] = vps_data

        # Get network information
        network_data = client.get_vps_network_info(vps.instance_id)
        monitoring_data['network'] = network_data

        # Get traffic usage
        traffic_data = client.get_vps_traffic(vps.instance_id)
        monitoring_data['traffic'] = traffic_data

    except DopraxAPIError as e:
        monitoring_data['error'] = str(e)

    context = {
        'vps': vps,
        'monitoring_data': monitoring_data,
    }
    return render(request, 'vps/monitoring.html', context)
