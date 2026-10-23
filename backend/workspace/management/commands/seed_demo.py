import os
from datetime import date, timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from workspace.models import Organization, Membership, Project, ProjectMembership, Task, AuditEvent


class Command(BaseCommand):
    help = 'Create a local development workspace. Never runs when DEBUG is false.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Demo seeding is allowed only in local DEBUG mode.')
        password = os.getenv('SPRINTLENS_DEMO_PASSWORD')
        if not password or len(password) < 12:
            raise CommandError('Set SPRINTLENS_DEMO_PASSWORD to at least 12 characters.')
        org, _ = Organization.objects.get_or_create(slug='studio', defaults={'name': 'Studio workspace'})
        members = []
        for username, first, last, role in [('alex', 'Alex', 'Morgan', 'Manager'), ('sarah', 'Sarah', 'Chen', 'Developer'), ('marcus', 'Marcus', 'Reed', 'Developer'), ('priya', 'Priya', 'Shah', 'Developer')]:
            user, created = User.objects.get_or_create(username=username, defaults={'first_name': first, 'last_name': last})
            if created:
                user.set_password(password)
                user.save()
            member, _ = Membership.objects.get_or_create(organization=org, user=user, defaults={'role': role})
            members.append(member)
        today = timezone.localdate()
        projects = []
        for name, code, color, description, offset in [('Customer Portal', 'CP', 'purple', 'A better home for every customer.', 12), ('Payments API', 'PA', 'orange', 'Reliable payments. Less friction.', 6), ('Design System', 'DS', 'green', 'One language across every product.', 19)]:
            project, _ = Project.objects.get_or_create(organization=org, code=code, defaults={'name': name, 'color': color, 'description': description, 'due': today + timedelta(days=offset)})
            for member in members:
                ProjectMembership.objects.get_or_create(project=project, membership=member, defaults={'is_reviewer': member.role == Membership.Role.MANAGER})
            projects.append(project)
        fixtures = [
            ('Build account settings experience', 0, 1, 'In progress', 'High', 4),
            ('Resolve payment webhook dependency', 1, 0, 'Blocked', 'High', 3),
            ('Review accessible form components', 2, 3, 'In review', 'Medium', 5),
            ('Add organization access controls', 0, 2, 'Done', 'High', 0),
            ('Document payment retry behavior', 1, 2, 'To do', 'Medium', 6),
            ('Publish color and spacing tokens', 2, 3, 'Done', 'Low', -1),
            ('Verify invitation acceptance flow', 0, 0, 'In review', 'Medium', 4),
        ]
        for title, project_index, assignee, status, priority, offset in fixtures:
            task, created = Task.objects.get_or_create(project=projects[project_index], title=title, defaults={'assignee': members[assignee], 'status': status, 'priority': priority, 'due': today + timedelta(days=offset), 'acceptance_criteria': 'Acceptance checks pass and the manager approves the deliverable.'})
            if created:
                AuditEvent.objects.create(project=task.project, task=task, actor=members[0].user, action='task.seeded', text=f'Initialized sample task: {title}', after={'status': status})
        self.stdout.write(self.style.SUCCESS('Workspace ready. Manager: alex. Developers: sarah, marcus, priya. Existing accounts were not reset.'))
