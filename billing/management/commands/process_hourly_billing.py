from django.core.management.base import BaseCommand
from billing.services import HourlyBillingService


class Command(BaseCommand):
    help = 'Process hourly billing for all active VPS instances'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='Number of hours to bill for (default: 1)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be billed without actually processing',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS(f'Starting hourly billing process for {hours} hour(s)...')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No actual billing will occur')
            )

        results = HourlyBillingService.process_hourly_billing_for_all_users(hours)

        successful_billings = 0
        failed_billings = 0
        total_deducted = 0

        for result in results:
            if result['success']:
                successful_billings += 1
                total_deducted += result['total_deducted']
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {result['user']}: {result['message']} (${result['total_deducted']})"
                    )
                )
            else:
                failed_billings += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ {result['user']}: {result['message']}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nBilling Summary:'
            )
        )
        self.stdout.write(
            f'Successful: {successful_billings}'
        )
        self.stdout.write(
            f'Failed: {failed_billings}'
        )
        self.stdout.write(
            f'Total Deducted: ${total_deducted}'
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('This was a dry run - no charges were processed')
            )