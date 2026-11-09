from rest_framework import serializers
from accounts.models import Employee
from accounts.serializers import EmployeePublicSerializer
from posts.models import Post
from .models import Conversation, Message


class SharedPostPreviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    author_avatar = serializers.CharField(source='author.avatar_url', read_only=True)
    author_employee_id = serializers.CharField(source='author.employee_id', read_only=True)
    author_department = serializers.CharField(source='author.department.name', default='', read_only=True)
    media_preview = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id',
            'author_name',
            'author_avatar',
            'author_employee_id',
            'author_department',
            'content',
            'media_preview',
            'created_at',
            'is_deleted',
        ]

    def get_media_preview(self, obj):
        first_media = obj.media_attachments.filter(is_deleted=False).first()
        if not first_media:
            return None
        return {
            'id': first_media.id,
            'file_type': first_media.file_type,
            'url': first_media.get_view_url(),
            'filename': first_media.original_filename,
        }


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_employee_id = serializers.CharField(source='sender.employee_id', read_only=True)
    sender_avatar = serializers.CharField(source='sender.avatar_url', read_only=True)
    shared_post = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'sender',
            'sender_employee_id',
            'sender_name',
            'sender_avatar',
            'content',
            'shared_post',
            'created_at',
            'is_read',
            'is_mine',
        ]
        read_only_fields = ['id', 'conversation', 'sender', 'created_at', 'is_mine']

    def get_is_mine(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender_id == request.user.id
        return False

    def get_shared_post(self, obj):
        if not obj.shared_post:
            return None
        if obj.shared_post.is_deleted:
            return {
                'id': obj.shared_post.id,
                'is_available': False,
                'message': 'This post is no longer available.'
            }
        data = SharedPostPreviewSerializer(obj.shared_post, context=self.context).data
        data['is_available'] = True
        return data


class ConversationSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'other_participant',
            'last_message',
            'unread_count',
            'updated_at',
            'created_at',
        ]

    def get_other_participant(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        other = obj.get_other_participant(request.user)
        if other:
            return EmployeePublicSerializer(other, context=self.context).data
        return None

    def get_last_message(self, obj):
        last = obj.last_message
        if last:
            snippet = last.content
            if not snippet and last.shared_post:
                snippet = "Shared a post"
            return {
                'id': last.id,
                'content': snippet,
                'has_shared_post': bool(last.shared_post_id),
                'sender_id': last.sender_id,
                'sender_name': last.sender.full_name,
                'created_at': last.created_at,
                'is_read': last.is_read,
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return obj.unread_count_for(request.user)
