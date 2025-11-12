from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from vps.models import VPSPlan
from vps.services.doprax_client import DopraxClient, DopraxAPIError
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync VPS plans from Doprax API into the database'

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
            self.stdout.write('Fetching plans from Doprax API...')
            logger.info('Starting VPS plans sync from Doprax API')

            # Get locations and plans data
            data = client.get_locations_and_plans()
            logger.info(f'Retrieved data for {len(data.get("locationsList", []))} locations')

            locations = data.get('locationsList', [])
            machine_mapping = data.get('locationMachineTypeMapping', {})

            # Create location mapping for easy lookup
            location_map = {loc['locationCode']: loc for loc in locations}

            plans_created = 0
            plans_updated = 0
            plans_processed = 0

            # Process each location's machine types
            for location_code, machines in machine_mapping.items():
                if not machines:
                    continue

                loc_info = location_map.get(location_code, {})
                location_name = loc_info.get('name', 'Unknown')
                provider = loc_info.get('provider', 'Unknown')

                for machine in machines:
                    plans_processed += 1

                    # Create plan name from machine details
                    plan_name = machine.get('name', f"{machine.get('cpu', 0)}CPU-{machine.get('ramGb', 0)}GB-{machine.get('ssdGb', 0)}GB")

                    # Check if plan already exists
                    plan, created = VPSPlan.objects.get_or_create(
                        name=plan_name,
                        defaults={
                            'cpu_cores': machine.get('cpu', 0),
                            'ram_gb': machine.get('ramGb', 0),
                            'disk_gb': machine.get('ssdGb', 0),
                            'bandwidth_gb': machine.get('monthlyTrafficGb', 0),
                            'price_per_month': machine.get('monthlyPriceUsd', 0),
                            'is_active': True,
                        }
                    )

                    if created:
                        plans_created += 1
                        if not dry_run:
                            self.stdout.write(
                                self.style.SUCCESS(f'Created plan: {plan_name}')
                            )
                        else:
                            self.stdout.write(f'Would create plan: {plan_name}')
                    else:
                        # Update existing plan if prices changed
                        updated = False
                        if plan.price_per_month != machine.get('monthlyPriceUsd', 0):
                            plan.price_per_month = machine.get('monthlyPriceUsd', 0)
                            updated = True

                        if plan.bandwidth_gb != machine.get('monthlyTrafficGb', 0):
                            plan.bandwidth_gb = machine.get('monthlyTrafficGb', 0)
                            updated = True

                        if updated:
                            if not dry_run:
                                plan.save()
                                plans_updated += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'Updated plan: {plan_name}')
                                )
                            else:
                                plans_updated += 1
                                self.stdout.write(f'Would update plan: {plan_name}')

            # Summary
            logger.info(f'Sync completed. Processed: {plans_processed}, Created: {plans_created}, Updated: {plans_updated}')
            self.stdout.write(self.style.SUCCESS(
                f'Sync completed. Processed: {plans_processed}, Created: {plans_created}, Updated: {plans_updated}'
            ))

        except DopraxAPIError as e:
            raise CommandError(f'API Error: {str(e)}')
        except Exception as e:
            logger.error(f'Unexpected error during plan sync: {str(e)}')
            raise CommandError(f'Unexpected error: {str(e)}')