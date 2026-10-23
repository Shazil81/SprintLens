"""The inbox is private to the currently signed-in workspace member."""
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .access import accessible_projects, current_membership
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'project', 'kind', 'title', 'body', 'read_at', 'created_at']


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        member = current_membership(self.request)
        return Notification.objects.filter(recipient=member, project__in=accessible_projects(member))

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        item = self.get_object()
        if not item.read_at:
            item.read_at = timezone.now()
            item.save(update_fields=['read_at'])
        return Response(self.get_serializer(item).data)

    @action(detail=False, methods=['post'])
    def read_all(self, request):
        self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({'detail': 'Inbox marked as read.'})
