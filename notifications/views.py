from rest_framework import status, viewsets, views
from rest_framework.response import Response
from rest_framework.decorators import action
from accounts.permissions import IsActiveEmployee
from .models import Notification
from .serializers import NotificationSerializer
from .services import check_and_dispatch_daily_birthdays

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsActiveEmployee]

    def get_queryset(self):
        check_and_dispatch_daily_birthdays()
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('sender', 'sender__department').order_by('-created_at')

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        check_and_dispatch_daily_birthdays()
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'detail': 'Notification marked as read.'})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'detail': 'All notifications marked as read.'})
