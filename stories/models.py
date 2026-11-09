import os
from django.db import models
from django.utils import timezone
from accounts.models import Employee


def story_media_upload_path(instance, filename):
    today = timezone.now().strftime('%Y/%m/%d')
    ext = os.path.splitext(filename)[1].lower()
    safe_name = f"story_{instance.author_id}_{int(timezone.now().timestamp())}{ext}"
    return f"stories/{today}/{safe_name}"


class StoryQuerySet(models.QuerySet):
    def active(self):
        """Returns only stories that have not expired."""
        return self.filter(expires_at__gt=timezone.now())

    def expired(self):
        """Returns stories that have passed their 12-hour expiration."""
        return self.filter(expires_at__lte=timezone.now())

    def purge_expired(self):
        """Permanently deletes expired stories and their local disk files."""
        expired_stories = list(self.expired())
        count = len(expired_stories)
        for story in expired_stories:
            try:
                if story.media_file:
                    story.media_file.delete(save=False)
            except Exception:
                pass
            story.delete()
        return count


class Story(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
        ('TEXT', 'Text Status'),
    ]

    author = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='stories'
    )
    media_file = models.FileField(upload_to=story_media_upload_path, blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='IMAGE')
    caption = models.CharField(max_length=500, blank=True, default='')
    background = models.CharField(max_length=50, blank=True, default='gradient-blue')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    objects = StoryQuerySet.as_manager()

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Story'
        verbose_name_plural = 'Stories'

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Ephemeral: Automatically expires 12 hours after creation
            self.expires_at = timezone.now() + timezone.timedelta(hours=12)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def view_count(self):
        return self.views.count()

    def __str__(self):
        return f"Story #{self.id} by {self.author.full_name} ({self.media_type})"


class StoryView(models.Model):
    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name='views'
    )
    viewer = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='viewed_stories'
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'viewer')
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.viewer.full_name} viewed Story #{self.story_id}"
