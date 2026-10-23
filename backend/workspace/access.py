from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from .models import Membership, Project


def current_membership(request):
    memberships = Membership.objects.filter(user=request.user).select_related('organization')
    organization = request.headers.get('X-Organization-ID')
    if organization:
        if not organization.isascii() or not organization.isdecimal() or len(organization) > 18:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'organization': 'Send a valid organization ID.'})
        return get_object_or_404(memberships, organization_id=organization)
    member = memberships.order_by('id').first()
    if member is None:
        raise PermissionDenied('Your account has no workspace membership.')
    return member


def accessible_projects(member):
    projects = Project.objects.filter(organization=member.organization)
    if member.role == Membership.Role.ADMIN:
        return projects
    return projects.filter(memberships__membership=member)


def require_manager(member):
    if member.role not in [Membership.Role.ADMIN, Membership.Role.MANAGER]:
        raise PermissionDenied('Only managers can create or assign work.')
