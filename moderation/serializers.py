from rest_framework import serializers
from accounts.serializers import EmployeePublicSerializer
from posts.serializers import PostSerializer, CommentSerializer
from .models import ContentReport, AuditLog

class ContentReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentReport
        fields = ['id', 'post', 'comment', 'reason', 'description']

    def validate(self, attrs):
        post = attrs.get('post')
        comment = attrs.get('comment')
        if not post and not comment:
            raise serializers.ValidationError("Either a post or comment must be selected for reporting.")
        if post and comment:
            raise serializers.ValidationError("Specify either a post or comment, not both in a single report.")
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        return ContentReport.objects.create(reporter=user, **validated_data)


class ContentReportSerializer(serializers.ModelSerializer):
    reporter_details = EmployeePublicSerializer(source='reporter', read_only=True)
    reviewed_by_details = EmployeePublicSerializer(source='reviewed_by', read_only=True)
    target_summary = serializers.SerializerMethodField()

    class Meta:
        model = ContentReport
        fields = [
            'id',
            'reporter',
            'reporter_details',
            'post',
            'comment',
            'target_summary',
            'reason',
            'description',
            'status',
            'reviewed_by',
            'reviewed_by_details',
            'admin_notes',
            'reviewed_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_target_summary(self, obj):
        request = self.context.get('request')
        if obj.post:
            media_urls = [m.get_view_url(request=request) for m in obj.post.media_attachments.all()]
            return {
                'type': 'POST',
                'id': obj.post.id,
                'author': obj.post.author.full_name or obj.post.author.username,
                'author_id': obj.post.author.id,
                'content': obj.post.content,
                'is_deleted': obj.post.is_deleted,
                'is_archived': getattr(obj.post, 'is_archived', False),
                'media_urls': media_urls,
                'created_at': obj.post.created_at.isoformat() if obj.post.created_at else None,
                'like_count': obj.post.like_count,
                'comment_count': obj.post.comment_count,
            }
        if obj.comment:
            return {
                'type': 'COMMENT',
                'id': obj.comment.id,
                'post_id': obj.comment.post_id,
                'author': obj.comment.author.full_name or obj.comment.author.username,
                'author_id': obj.comment.author.id,
                'content': obj.comment.content,
                'is_deleted': obj.comment.is_deleted,
                'created_at': obj.comment.created_at.isoformat() if obj.comment.created_at else None,
            }
        return None


class ContentReportReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['RESOLVED', 'DISMISSED'])
    remove_content = serializers.BooleanField(default=False)
    archive_content = serializers.BooleanField(default=False)
    admin_notes = serializers.CharField(required=False, allow_blank=True, default='')


class AuditLogSerializer(serializers.ModelSerializer):
    actor_details = EmployeePublicSerializer(source='actor', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'actor',
            'actor_details',
            'action',
            'target_model',
            'target_id',
            'details',
            'ip_address',
            'created_at',
        ]
        read_only_fields = fields

