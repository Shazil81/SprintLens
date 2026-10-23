from django.core.management.base import BaseCommand
from workspace.tasks import generate_digests, generate_reminders


class Command(BaseCommand):
    help = 'Generate durable reminder/digest notifications once, without a running broker.'

    def handle(self, *args, **options):
        count = generate_reminders() + generate_digests()
        self.stdout.write(self.style.SUCCESS(f'Created {count} notifications.'))
