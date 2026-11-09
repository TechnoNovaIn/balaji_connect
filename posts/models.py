from django.db import models
from django.conf import settings

class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    content = models.TextField(blank=True, default='', help_text="Text content of the post")
    media_attachments = models.ManyToManyField(
        'media_vault.MediaAttachment',
        blank=True,
        related_name='posts'
    )
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['is_deleted', 'is_archived', '-created_at', '-id']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self):
        snippet = (self.content[:30] + '...') if len(self.content) > 30 else self.content
        return f"Post #{self.pk} by {self.author.employee_id}: {snippet or '[Media Only]'}"


class PostReaction(models.Model):
    class ReactionType(models.TextChoices):
        LIKE = 'LIKE', 'Like'
        LOVE = 'LOVE', 'Love'
        HAHA = 'HAHA', 'Haha'
        WOW = 'WOW', 'Wow'
        SAD = 'SAD', 'Sad'
        ANGRY = 'ANGRY', 'Angry'

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    reaction_type = models.CharField(
        max_length=20,
        choices=ReactionType.choices,
        default=ReactionType.LIKE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['post', 'user'],
                name='unique_user_post_reaction'
            )
        ]
        indexes = [
            models.Index(fields=['post', 'reaction_type']),
        ]

    def __str__(self):
        return f"{self.user.employee_id} {self.reaction_type} post #{self.post_id}"


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    content = models.TextField(max_length=2000)
    like_count = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'is_deleted', 'created_at']),
        ]

    def __str__(self):
        return f"Comment #{self.pk} by {self.author.employee_id} on Post #{self.post_id}"


class CommentReaction(models.Model):
    class ReactionType(models.TextChoices):
        LIKE = 'LIKE', 'Like'
        LOVE = 'LOVE', 'Love'
        HAHA = 'HAHA', 'Haha'
        WOW = 'WOW', 'Wow'
        SAD = 'SAD', 'Sad'
        ANGRY = 'ANGRY', 'Angry'

    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_reactions'
    )
    reaction_type = models.CharField(
        max_length=20,
        choices=ReactionType.choices,
        default=ReactionType.LIKE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['comment', 'user'],
                name='unique_user_comment_reaction'
            )
        ]
        indexes = [
            models.Index(fields=['comment', 'reaction_type']),
        ]

    def __str__(self):
        return f"{self.user} {self.reaction_type} on comment #{self.comment_id}"
