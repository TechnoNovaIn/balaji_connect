from django.db import models
from django.conf import settings

class ContentReport(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        RESOLVED = 'RESOLVED', 'Resolved (Action Taken)'
        DISMISSED = 'DISMISSED', 'Dismissed (No Action)'

    class Reason(models.TextChoices):
        INAPPROPRIATE = 'INAPPROPRIATE', 'Inappropriate or offensive content'
        HARASSMENT = 'HARASSMENT', 'Harassment or bullying'
        CONFIDENTIAL = 'CONFIDENTIAL', 'Breach of company confidentiality'
        SPAM = 'SPAM', 'Spam or unauthorized advertising'
        OTHER = 'OTHER', 'Other policy violation'

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='filed_reports'
    )
    post = models.ForeignKey(
        'posts.Post',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )
    comment = models.ForeignKey(
        'posts.Comment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )
    reason = models.CharField(
        max_length=50,
        choices=Reason.choices,
        default=Reason.INAPPROPRIATE
    )
    description = models.TextField(blank=True, help_text="Additional context provided by reporter")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_reports'
    )
    admin_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"Report #{self.pk} by {self.reporter.employee_id} ({self.status})"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events'
    )
    action = models.CharField(max_length=100, db_index=True)
    target_model = models.CharField(max_length=50)
    target_id = models.CharField(max_length=50)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.CharField(max_length=45, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor_id = self.actor.employee_id if self.actor else "SYSTEM"
        return f"[{self.created_at}] {actor_id} -> {self.action} on {self.target_model}:{self.target_id}"
