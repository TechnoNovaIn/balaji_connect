from rest_framework import serializers
from accounts.serializers import EmployeePublicSerializer
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    sender_details = EmployeePublicSerializer(source='sender', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'sender',
            'sender_details',
            'notification_type',
            'target_post',
            'target_comment',
            'title',
            'message',
            'is_read',
            'created_at',
        ]
        read_only_fields = fields

