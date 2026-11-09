from django.db import models
from django.conf import settings
from django.urls import reverse

class MediaAttachment(models.Model):
    class FileType(models.TextChoices):
        IMAGE = 'IMAGE', 'Image'
        VIDEO = 'VIDEO', 'Video'

    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_media'
    )
    storage_provider = models.CharField(
        max_length=50,
        default='local',
        help_text="Underlying storage backend (e.g. 'local', 'gdrive')"
    )
    storage_file_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="File identifier within the storage provider"
    )
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(
        max_length=10,
        choices=FileType.choices,
        default=FileType.IMAGE
    )
    mime_type = models.CharField(max_length=100)
    file_size_bytes = models.PositiveBigIntegerField()
    file_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA-256 hash to prevent duplicate uploads during retries"
    )
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uploader', '-created_at']),
            models.Index(fields=['file_hash', 'is_deleted']),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.file_type}) - {self.storage_file_id}"

    def get_view_url(self, request=None):
        url = reverse('media-view', kwargs={'pk': self.pk})
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    @property
    def file_url(self):
        return self.get_view_url()
