from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Conversation(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        help_text=_("Participants in this private conversation")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Conversation')
        verbose_name_plural = _('Conversations')

    def __str__(self):
        participant_names = ", ".join([p.employee_id for p in self.participants.all()[:2]])
        return f"Conversation #{self.id} ({participant_names})"

    def get_other_participant(self, current_user):
        """Returns the other employee in this 1-on-1 conversation."""
        return self.participants.exclude(id=current_user.id).first()

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()

    def unread_count_for(self, user):
        """Counts unread messages sent by the other party."""
        return self.messages.exclude(sender=user).filter(is_read=False).count()


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField(max_length=5000, blank=True, default='')
    shared_post = models.ForeignKey(
        'posts.Post',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shared_in_messages'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')

    def __str__(self):
        return f"Msg #{self.id} from {self.sender.employee_id}: {self.content[:30]}"
