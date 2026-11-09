from django.core.management.base import BaseCommand
from notifications.services import check_and_dispatch_daily_birthdays

class Command(BaseCommand):
    help = 'Checks for employees celebrating birthdays today and dispatches company-wide notifications.'

    def handle(self, *args, **options):
        sent = check_and_dispatch_daily_birthdays()
        self.stdout.write(self.style.SUCCESS(f"Successfully processed birthday notifications. Dispatched: {sent}"))

