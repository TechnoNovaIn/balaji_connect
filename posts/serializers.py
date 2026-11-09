from rest_framework import serializers
from accounts.serializers import EmployeePublicSerializer
from media_vault.models import MediaAttachment
from media_vault.serializers import MediaAttachmentSerializer
from .models import Post, PostReaction, Comment

class CommentSerializer(serializers.ModelSerializer):
    author_details = EmployeePublicSerializer(source='author', read_only=True)
    post_id = serializers.IntegerField(source='post.id', read_only=True)
    post_snippet = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(read_only=True)
    user_reaction = serializers.SerializerMethodField()
    has_reacted = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id',
            'post',
            'post_id',
            'post_snippet',
            'author',
            'author_details',
            'content',
            'like_count',
            'user_reaction',
            'has_reacted',
            'is_owner',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'post', 'post_id', 'post_snippet', 'author', 'like_count', 'created_at', 'updated_at']

    def get_post_snippet(self, obj):
        if obj.post and obj.post.content:
            text = obj.post.content.strip()
            return (text[:60] + '...') if len(text) > 60 else text
        return "Media Post"

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user or request.user.is_administrator

    def get_user_reaction(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        reaction = obj.reactions.filter(user=request.user).first()
        return reaction.reaction_type if reaction else None

    def get_has_reacted(self, obj):
        return bool(self.get_user_reaction(obj))

    def validate_content(self, value):
        text = value.strip()
        if not text:
            raise serializers.ValidationError("Comment content cannot be empty.")
        if len(text) > 2000:
            raise serializers.ValidationError("Comment cannot exceed 2000 characters.")
        return text


class PostSerializer(serializers.ModelSerializer):
    author_details = EmployeePublicSerializer(source='author', read_only=True)
    media_attachments = MediaAttachmentSerializer(many=True, read_only=True)
    media_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list
    )
    has_reacted = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id',
            'author',
            'author_details',
            'content',
            'media_attachments',
            'media_ids',
            'like_count',
            'comment_count',
            'has_reacted',
            'user_reaction',
            'is_owner',
            'is_archived',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'author',
            'like_count',
            'comment_count',
            'has_reacted',
            'user_reaction',
            'is_owner',
            'is_archived',
            'created_at',
            'updated_at',
        ]

    def get_user_reaction(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        reaction = obj.reactions.filter(user=request.user).first()
        return reaction.reaction_type if reaction else None

    def get_has_reacted(self, obj):
        return bool(self.get_user_reaction(obj))

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user or request.user.is_administrator

    def validate(self, attrs):
        content = attrs.get('content', '').strip()
        media_ids = attrs.get('media_ids', [])

        if not content and not media_ids:
            raise serializers.ValidationError("A post must contain text content or at least one media attachment.")
        return attrs

    def create(self, validated_data):
        media_ids = validated_data.pop('media_ids', [])
        user = self.context['request'].user
        post = Post.objects.create(author=user, **validated_data)

        if media_ids:
            # Ensure only attachments uploaded by this user and not deleted can be attached
            valid_attachments = MediaAttachment.objects.filter(
                id__in=media_ids,
                uploader=user,
                is_deleted=False
            )
            post.media_attachments.set(valid_attachments)

        return post


class PostReactionSerializer(serializers.ModelSerializer):
    user_details = EmployeePublicSerializer(source='user', read_only=True)

    class Meta:
        model = PostReaction
        fields = ['id', 'post', 'user', 'user_details', 'reaction_type', 'created_at']
        read_only_fields = fields

