from django.core.management.base import BaseCommand
from stories.models import Story


class Command(BaseCommand):
    help = 'Purges expired stories (> 12 hours old) and deletes their local media files from disk'

    def handle(self, *args, **options):
        deleted_count = Story.objects.purge_expired()
        self.stdout.write(self.style.SUCCESS(f"Successfully purged {deleted_count} expired stories."))

