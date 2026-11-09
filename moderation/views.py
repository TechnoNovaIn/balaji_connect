from django.utils import timezone
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from accounts.permissions import IsActiveEmployee, IsAdminRole
from .models import ContentReport, AuditLog
from .serializers import (
    ContentReportSerializer,
    ContentReportCreateSerializer,
    ContentReportReviewSerializer,
    AuditLogSerializer,
)

class ContentReportViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action == 'create':
            return [IsActiveEmployee()]
        return [IsAdminRole()]

    def get_serializer_class(self):
        if self.action == 'create':
            return ContentReportCreateSerializer
        return ContentReportSerializer

    def get_queryset(self):
        qs = ContentReport.objects.select_related(
            'reporter',
            'reporter__department',
            'reviewed_by',
            'post',
            'post__author',
            'comment',
            'comment__author'
        ).prefetch_related(
            'post__media_attachments'
        ).order_by('-created_at')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs

    def perform_create(self, serializer):
        report = serializer.save()
        try:
            from accounts.models import Employee
            from notifications.models import Notification

            admins = Employee.objects.filter(role=Employee.Role.ADMIN, is_active=True)
            reporter_name = self.request.user.full_name or self.request.user.username
            target_type = "Post" if report.post_id else "Comment"
            target_id = report.post_id or report.comment_id
            reason_label = report.get_reason_display()

            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    sender=self.request.user,
                    notification_type=Notification.NotificationType.SYSTEM,
                    target_post=report.post,
                    target_comment=report.comment,
                    title="⚠️ Content Flagged for Moderation",
                    message=f"{reporter_name} reported {target_type} #{target_id} ({reason_label}). Review in Admin Dashboard."
                )
        except Exception:
            pass

    @action(detail=True, methods=['post'], permission_classes=[IsAdminRole])
    def review(self, request, pk=None):
        report = self.get_object()
        serializer = ContentReportReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        remove_content = serializer.validated_data.get('remove_content', False)
        archive_content = serializer.validated_data.get('archive_content', False)
        admin_notes = serializer.validated_data.get('admin_notes', '')

        with transaction.atomic():
            report.status = new_status
            report.admin_notes = admin_notes
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save()

            if remove_content:
                if report.post:
                    report.post.is_deleted = True
                    report.post.save(update_fields=['is_deleted'])
                    AuditLog.objects.create(
                        actor=request.user,
                        action='MODERATION_REMOVE_POST',
                        target_model='Post',
                        target_id=str(report.post.id),
                        details={'report_id': report.id, 'reason': report.reason},
                        ip_address=request.META.get('REMOTE_ADDR', '')
                    )
                elif report.comment:
                    report.comment.is_deleted = True
                    report.comment.save(update_fields=['is_deleted'])
                    AuditLog.objects.create(
                        actor=request.user,
                        action='MODERATION_REMOVE_COMMENT',
                        target_model='Comment',
                        target_id=str(report.comment.id),
                        details={'report_id': report.id, 'reason': report.reason},
                        ip_address=request.META.get('REMOTE_ADDR', '')
                    )
            elif archive_content and report.post:
                report.post.is_archived = True
                report.post.save(update_fields=['is_archived'])
                AuditLog.objects.create(
                    actor=request.user,
                    action='MODERATION_ARCHIVE_POST',
                    target_model='Post',
                    target_id=str(report.post.id),
                    details={'report_id': report.id, 'reason': report.reason},
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )

            AuditLog.objects.create(
                actor=request.user,
                action=f'MODERATION_REPORT_{new_status}',
                target_model='ContentReport',
                target_id=str(report.id),
                details={
                    'status': new_status,
                    'remove_content': remove_content,
                    'archive_content': archive_content
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )

        return Response(ContentReportSerializer(report, context={'request': request}).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.select_related('actor', 'actor__department').order_by('-created_at')
