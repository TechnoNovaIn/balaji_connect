from django.db import models
from django.conf import settings

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        REACTION = 'REACTION', 'Reaction'
        COMMENT = 'COMMENT', 'Comment'
        ANNOUNCEMENT = 'ANNOUNCEMENT', 'Announcement'
        BIRTHDAY = 'BIRTHDAY', 'Birthday'
        SYSTEM = 'SYSTEM', 'System'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )
    target_post = models.ForeignKey(
        'posts.Post',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    target_comment = models.ForeignKey(
        'posts.Comment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    title = models.CharField(max_length=150)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.employee_id}: {self.title}"
