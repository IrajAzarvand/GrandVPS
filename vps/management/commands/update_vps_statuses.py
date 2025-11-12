from django.core.management.base import BaseCommand, CommandError
from vps.models import VPSInstance
from vps.services.doprax_client import DopraxClient, DopraxAPIError
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update status of all VPS instances from Doprax API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        try:
            client = DopraxClient()
            vps_instances = VPSInstance.objects.all()

            if not vps_instances:
                self.stdout.write('No VPS instances found in database')
                return

            updated_count = 0
            error_count = 0

            for vps in vps_instances:
                try:
                    # Get current status from API
                    status_data = client.get_vps_status(vps.instance_id)

                    new_status = status_data.get('status', '').lower()
                    new_ip = status_data.get('ipv4')

                    # Map API status to our model status
                    status_mapping = {
                        'active': 'active',
                        'running': 'active',
                        'stopped': 'stopped',
                        'pending': 'pending',
                        'terminated': 'terminated',
                        'suspended': 'suspended',
                    }

                    mapped_status = status_mapping.get(new_status, 'pending')

                    # Check if status or IP changed
                    status_changed = vps.status != mapped_status
                    ip_changed = (new_ip and vps.ip_address != new_ip)

                    if status_changed or ip_changed:
                        if not dry_run:
                            vps.status = mapped_status
                            if new_ip:
                                vps.ip_address = new_ip
                            vps.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Updated {vps.instance_id}: status={mapped_status}, ip={new_ip or "unchanged"}'
                                )
                            )
                        else:
                            updated_count += 1
                            self.stdout.write(
                                f'Would update {vps.instance_id}: status={mapped_status}, ip={new_ip or "unchanged"}'
                            )
                    else:
                        self.stdout.write(f'No changes needed for {vps.instance_id}')

                except DopraxAPIError as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'Error updating {vps.instance_id}: {str(e)}')
                    )
                except Exception as e:
                    error_count += 1
                    logger.error(f'Unexpected error updating VPS {vps.instance_id}: {str(e)}')
                    self.stdout.write(
                        self.style.ERROR(f'Unexpected error updating {vps.instance_id}: {str(e)}')
                    )

            # Summary
            self.stdout.write(self.style.SUCCESS(
                f'Status update completed. Updated: {updated_count}, Errors: {error_count}'
            ))

        except DopraxAPIError as e:
            raise CommandError(f'API Error: {str(e)}')
        except Exception as e:
            logger.error(f'Unexpected error during status update: {str(e)}')
            raise CommandError(f'Unexpected error: {str(e)}')