from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from .models import Invoice
from vps.models import VPSInstance
from wallet.models import Wallet, Transaction


class HourlyBillingService:
    """Service for handling hourly billing operations"""

    @staticmethod
    def calculate_hourly_cost(vps_instance):
        """Calculate hourly cost for a VPS instance with 10% profit margin"""
        monthly_cost = vps_instance.plan.price_per_month
        hourly_base = monthly_cost / Decimal('720')  # 30 days * 24 hours
        hourly_with_margin = hourly_base * Decimal('1.10')  # 10% profit margin
        return hourly_with_margin.quantize(Decimal('0.01'))

    @staticmethod
    def process_hourly_billing_for_user(user, hours=1):
        """Process hourly billing for all active VPS instances of a user"""
        active_instances = VPSInstance.objects.filter(
            user=user,
            status='active'
        )

        if not active_instances.exists():
            return {'success': True, 'message': 'No active VPS instances to bill', 'total_deducted': Decimal('0')}

        try:
            with transaction.atomic():
                wallet = Wallet.objects.get(user=user)
                total_cost = Decimal('0')

                for instance in active_instances:
                    hourly_cost = HourlyBillingService.calculate_hourly_cost(instance)
                    cost_for_hours = hourly_cost * hours
                    total_cost += cost_for_hours

                if wallet.balance < total_cost:
                    return {
                        'success': False,
                        'message': f'Insufficient balance. Required: ${total_cost}, Available: ${wallet.balance}',
                        'total_deducted': Decimal('0')
                    }

                # Deduct from wallet
                wallet.withdraw(total_cost, f'Hourly billing for {len(active_instances)} VPS instances ({hours} hours)')

                # Send notification
                NotificationService.send_hourly_billing_notification(user, total_cost, len(active_instances))

                return {
                    'success': True,
                    'message': f'Successfully billed ${total_cost} for {len(active_instances)} VPS instances',
                    'total_deducted': total_cost
                }

        except Wallet.DoesNotExist:
            return {'success': False, 'message': 'User wallet not found', 'total_deducted': Decimal('0')}
        except Exception as e:
            return {'success': False, 'message': f'Billing error: {str(e)}', 'total_deducted': Decimal('0')}

    @staticmethod
    def process_hourly_billing_for_all_users(hours=1):
        """Process hourly billing for all users with active VPS instances"""
        results = []
        users_with_active_vps = VPSInstance.objects.filter(
            status='active'
        ).values_list('user', flat=True).distinct()

        for user_id in users_with_active_vps:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(id=user_id)
                result = HourlyBillingService.process_hourly_billing_for_user(user, hours)
                results.append({
                    'user': user.username,
                    'success': result['success'],
                    'message': result['message'],
                    'total_deducted': result['total_deducted']
                })
            except User.DoesNotExist:
                results.append({
                    'user': f'User {user_id}',
                    'success': False,
                    'message': 'User not found',
                    'total_deducted': Decimal('0')
                })

        return results


class NotificationService:
    """Service for sending billing notifications"""

    @staticmethod
    def send_low_balance_notification(user, current_balance, required_balance):
        """Send notification when wallet balance is low"""
        subject = 'GrandVPS - Low Wallet Balance Warning'
        message = f"""
        Dear {user.username},

        Your wallet balance is running low.

        Current Balance: ${current_balance}
        Recommended Minimum: ${required_balance}

        Please top up your wallet to avoid service interruptions.

        Best regards,
        GrandVPS Team
        """

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            # Log error but don't fail the operation
            pass

    @staticmethod
    def send_payment_due_notification(user, invoice):
        """Send notification for payment due"""
        subject = 'GrandVPS - Payment Due'
        message = f"""
        Dear {user.username},

        Your invoice #{invoice.invoice_number} is due for payment.

        Amount: ${invoice.amount}
        Due Date: {invoice.due_date}

        Please ensure payment is made before the due date to avoid service suspension.

        Best regards,
        GrandVPS Team
        """

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            pass

    @staticmethod
    def send_renewal_success_notification(user, instance, cost):
        """Send notification for successful renewal"""
        subject = 'GrandVPS - VPS Renewal Successful'
        message = f"""
        Dear {user.username},

        Your VPS instance {instance.instance_id} has been successfully renewed.

        Plan: {instance.plan.name}
        Cost: ${cost}
        New Expiry: {instance.expires_at.strftime('%Y-%m-%d')}

        Best regards,
        GrandVPS Team
        """

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            pass

    @staticmethod
    def send_renewal_failure_notification(user, instance):
        """Send notification for renewal failure"""
        subject = 'GrandVPS - VPS Renewal Failed'
        message = f"""
        Dear {user.username},

        We were unable to renew your VPS instance {instance.instance_id} due to insufficient wallet balance.

        The instance has been suspended. Please top up your wallet and contact support to reactivate.

        Plan: {instance.plan.name}

        Best regards,
        GrandVPS Team
        """

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            pass

    @staticmethod
    def send_hourly_billing_notification(user, total_cost, instances_count):
        """Send notification for hourly billing"""
        subject = 'GrandVPS - Hourly Billing Completed'
        message = f"""
        Dear {user.username},

        Your hourly billing has been processed.

        Instances Billed: {instances_count}
        Total Cost: ${total_cost}

        Best regards,
        GrandVPS Team
        """

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            pass

    @staticmethod
    def check_wallet_balance_for_renewal(user):
        """Check if user has sufficient balance for VPS renewal"""
        active_instances = VPSInstance.objects.filter(
            user=user,
            status='active'
        )

        if not active_instances.exists():
            return {'sufficient': True, 'message': 'No active instances to renew'}

        try:
            wallet = Wallet.objects.get(user=user)
            total_hourly_cost = sum(
                HourlyBillingService.calculate_hourly_cost(instance)
                for instance in active_instances
            )

            # Check for 24 hours renewal
            required_balance = total_hourly_cost * 24

            return {
                'sufficient': wallet.balance >= required_balance,
                'current_balance': wallet.balance,
                'required_balance': required_balance,
                'message': f'Balance: ${wallet.balance}, Required for 24h: ${required_balance}'
            }

        except Wallet.DoesNotExist:
            return {'sufficient': False, 'message': 'Wallet not found'}


class InvoiceService:
    """Service for generating and managing invoices"""

    @staticmethod
    def generate_invoice_pdf(invoice):
        """Generate PDF for an invoice"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title = Paragraph("GrandVPS Invoice", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))

        # Invoice details
        invoice_data = [
            ['Invoice Number:', invoice.invoice_number],
            ['Date:', invoice.issued_date.strftime('%Y-%m-%d')],
            ['Due Date:', invoice.due_date.strftime('%Y-%m-%d')],
            ['Status:', invoice.get_status_display()],
            ['Amount:', f'${invoice.amount}'],
        ]

        if invoice.billing_cycle:
            invoice_data.extend([
                ['Billing Period:', f'{invoice.billing_cycle.start_date} to {invoice.billing_cycle.end_date}'],
            ])

        # Customer info
        customer_data = [
            ['Customer:', invoice.user.username],
            ['Email:', invoice.user.email],
        ]

        # Create tables
        invoice_table = Table(invoice_data)
        invoice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        customer_table = Table(customer_data)
        customer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(invoice_table)
        story.append(Spacer(1, 12))
        story.append(customer_table)
        story.append(Spacer(1, 12))

        # Footer
        footer = Paragraph("Thank you for using GrandVPS!", styles['Normal'])
        story.append(footer)

        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def create_invoice_for_billing_cycle(billing_cycle, vps_instances):
        """Create an invoice for a billing cycle"""
        invoice = Invoice.objects.create(
            user=billing_cycle.user,
            billing_cycle=billing_cycle,
            invoice_number=Invoice.generate_invoice_number(),
            amount=billing_cycle.amount,
            due_date=billing_cycle.end_date,
        )

        # Generate PDF
        pdf_buffer = InvoiceService.generate_invoice_pdf(invoice)
        invoice.pdf_file.save(f'invoice_{invoice.invoice_number}.pdf', pdf_buffer, save=True)

        return invoice


class AutoRenewalService:
    """Service for handling automatic VPS renewal"""

    @staticmethod
    def process_auto_renewal_for_user(user):
        """Process auto-renewal for all expired VPS instances of a user"""
        expired_instances = VPSInstance.objects.filter(
            user=user,
            status='active'
        ).filter(expires_at__lt=timezone.now())

        if not expired_instances.exists():
            return {'success': True, 'message': 'No expired instances to renew', 'renewed_count': 0}

        renewed_count = 0
        failed_count = 0
        total_cost = Decimal('0')

        try:
            with transaction.atomic():
                wallet = Wallet.objects.get(user=user)

                for instance in expired_instances:
                    # Calculate renewal cost (30 days)
                    monthly_cost = instance.plan.price_per_month
                    renewal_cost = monthly_cost  # For 30 days

                    if wallet.balance >= renewal_cost:
                        # Deduct from wallet
                        wallet.withdraw(renewal_cost, f'Auto-renewal for VPS {instance.instance_id} (30 days)')

                        # Renew the instance
                        instance.renew(days=30)
                        renewed_count += 1
                        total_cost += renewal_cost

                        # Send success notification
                        NotificationService.send_renewal_success_notification(user, instance, renewal_cost)
                    else:
                        # Insufficient funds - suspend the instance
                        instance.status = 'suspended'
                        instance.save()
                        failed_count += 1

                        # Send failure notification
                        NotificationService.send_renewal_failure_notification(user, instance)

                return {
                    'success': True,
                    'message': f'Renewed {renewed_count} instances, suspended {failed_count} due to insufficient funds',
                    'renewed_count': renewed_count,
                    'suspended_count': failed_count,
                    'total_cost': total_cost
                }

        except Wallet.DoesNotExist:
            return {'success': False, 'message': 'User wallet not found', 'renewed_count': 0}

    @staticmethod
    def process_auto_renewal_for_all_users():
        """Process auto-renewal for all users with expired VPS instances"""
        results = []
        users_with_expired_vps = VPSInstance.objects.filter(
            status='active',
            expires_at__lt=timezone.now()
        ).values_list('user', flat=True).distinct()

        for user_id in users_with_expired_vps:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(id=user_id)
                result = AutoRenewalService.process_auto_renewal_for_user(user)
                results.append({
                    'user': user.username,
                    'success': result['success'],
                    'message': result['message'],
                    'renewed_count': result.get('renewed_count', 0),
                    'suspended_count': result.get('suspended_count', 0),
                    'total_cost': result.get('total_cost', Decimal('0'))
                })
            except User.DoesNotExist:
                results.append({
                    'user': f'User {user_id}',
                    'success': False,
                    'message': 'User not found',
                    'renewed_count': 0,
                    'suspended_count': 0,
                    'total_cost': Decimal('0')
                })

        return results