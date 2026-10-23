"""Provide a local-only owner account without changing the existing manager's role."""
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from workspace.models import AuditEvent, Membership, Organization


class Command(BaseCommand):
    help = 'Create a local sample admin for the studio workspace; never resets existing users.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Local bootstrap is disabled outside DEBUG.')
        password = os.getenv('SPRINTLENS_DEMO_PASSWORD')
        if not password or len(password) < 12:
            raise CommandError('Configure a development demo password.')
        org = Organization.objects.select_for_update().get(slug='studio')
        if Membership.objects.filter(organization=org, role='Admin', user__is_active=True).exists():
            self.stdout.write('Workspace already has an admin; no accounts were changed.')
            return
        if get_user_model().objects.filter(username='admin').exists():
            raise CommandError('Username admin is already taken. No existing account was modified.')
        user = get_user_model().objects.create_user(username='admin', first_name='Workspace', last_name='Admin', password=password)
        member = Membership.objects.create(organization=org, user=user, role='Admin')
        AuditEvent.objects.create(organization=org, actor=user, action='member.bootstrap',
                                  text='Created local workspace admin', after={'member_id': member.pk, 'role': 'Admin'})
        self.stdout.write(self.style.SUCCESS('Local admin ready: username admin; password uses the private demo_password. Existing manager/developer accounts unchanged.'))
