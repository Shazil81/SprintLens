"""Create a fresh real workspace owner without demo seeding or a reusable password argument."""
import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_slug
from django.db import IntegrityError, transaction
from workspace.models import AuditEvent, Membership, Organization


class Command(BaseCommand):
    help = 'Create a new organization and its first workspace Admin. Password is prompted privately.'

    def add_arguments(self, parser):
        parser.add_argument('--organization-name',required=True)
        parser.add_argument('--organization-slug',required=True)
        parser.add_argument('--username',required=True)

    def handle(self, *args, **options):
        name,slug,username = (options[key].strip() for key in ['organization_name','organization_slug','username'])
        user_model = get_user_model()
        user = user_model(username=username)
        try:
            validate_slug(slug)
            user.full_clean(exclude=['password'])
        except ValidationError:
            raise CommandError('Choose a valid, unused username and organization slug.') from None
        if not name or len(name)>120 or not slug or len(slug)>50:
            raise CommandError('Choose an organization name (1-120 characters) and slug (1-50).')
        if Organization.objects.filter(slug=slug).exists() or user_model.objects.filter(username=username).exists():
            raise CommandError('Organization or username already exists. Existing accounts are never modified.')
        password = getpass.getpass('New owner password (hidden): ')
        if password != getpass.getpass('Confirm password (hidden): '):
            raise CommandError('Passwords do not match. No account created.')
        try:
            validate_password(password,user)
        except ValidationError as error:
            raise CommandError(' '.join(error.messages)) from None
        try:
            with transaction.atomic():
                organization = Organization.objects.create(name=name,slug=slug)
                user.set_password(password)
                user.save()
                membership = Membership.objects.create(organization=organization,user=user,role='Admin')
                AuditEvent.objects.create(organization=organization,actor=user,action='workspace.bootstrap',
                    text='Created a workspace and its first Admin',after={'member_id':membership.pk,'role':'Admin'})
        except IntegrityError:
            raise CommandError('Organization or username was created concurrently. No existing account was changed.') from None
        self.stdout.write(self.style.SUCCESS('Workspace Admin created. Sign in through the React application.'))
