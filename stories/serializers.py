import os
from rest_framework import serializers
from .models import Story, StoryView


class StoryViewerSerializer(serializers.ModelSerializer):
    viewer = serializers.SerializerMethodField()
    id = serializers.IntegerField(source='viewer.id', read_only=True)
    full_name = serializers.CharField(source='viewer.full_name', read_only=True)
    avatar_url = serializers.CharField(source='viewer.avatar_url', read_only=True)
    department_name = serializers.SerializerMethodField()

    class Meta:
        model = StoryView
        fields = ['id', 'viewer', 'full_name', 'avatar_url', 'department_name', 'viewed_at']

    def get_department_name(self, obj):
        v = obj.viewer
        return v.department.name if (v and getattr(v, 'department', None)) else 'Balaji Transports'

    def get_viewer(self, obj):
        v = obj.viewer
        dept_name = v.department.name if (v and getattr(v, 'department', None)) else 'Balaji Transports'
        return {
            'id': v.id,
            'full_name': v.full_name,
            'first_name': v.first_name or v.full_name,
            'avatar_url': v.avatar_url,
            'department_name': dept_name,
        }


class StoryItemSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    is_viewed = serializers.SerializerMethodField()
    has_seen = serializers.SerializerMethodField()
    seen_by_count = serializers.IntegerField(source='view_count', read_only=True)
    viewers = serializers.SerializerMethodField()
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    author_avatar = serializers.CharField(source='author.avatar_url', read_only=True)
    author = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            'id',
            'author_id',
            'author_name',
            'author_avatar',
            'author',
            'media_url',
            'media_type',
            'caption',
            'background',
            'created_at',
            'expires_at',
            'view_count',
            'seen_by_count',
            'is_viewed',
            'has_seen',
            'viewers',
        ]

    def get_has_seen(self, obj):
        return self.get_is_viewed(obj)

    def get_author(self, obj):
        return {
            'id': obj.author.id,
            'full_name': obj.author.full_name,
            'first_name': obj.author.first_name or obj.author.full_name,
            'avatar_url': obj.author.avatar_url,
            'username': obj.author.username,
        }

    def get_media_url(self, obj):
        if not obj.media_file:
            return None
        request = self.context.get('request')
        url = obj.media_file.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_is_viewed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # If user is author, mark as viewed
        if obj.author_id == request.user.id:
            return True
        # Check if user has viewed this story
        viewed_ids = self.context.get('viewed_story_ids')
        if viewed_ids is not None:
            return obj.id in viewed_ids
        return obj.views.filter(viewer=request.user).exists()

    def get_viewers(self, obj):
        request = self.context.get('request')
        # Only author (or admin) can see who viewed their story
        if request and request.user.is_authenticated:
            if obj.author_id == request.user.id or request.user.is_staff:
                views = obj.views.select_related('viewer').all()
                return StoryViewerSerializer(views, many=True).data
        return []


class UserStoryGroupSerializer(serializers.Serializer):
    author_id = serializers.IntegerField()
    author_name = serializers.CharField()
    author_avatar = serializers.CharField(allow_blank=True, allow_null=True)
    author = serializers.DictField(required=False)
    has_unseen = serializers.BooleanField()
    stories_count = serializers.IntegerField()
    stories = StoryItemSerializer(many=True)


class StoryCreateSerializer(serializers.ModelSerializer):
    media_file = serializers.FileField(required=False, allow_null=True)
    caption = serializers.CharField(max_length=500, required=False, allow_blank=True)
    background = serializers.CharField(max_length=50, required=False, allow_blank=True, default='gradient-blue')

    ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    ALLOWED_VIDEO_EXTS = {'.mp4', '.mov', '.webm'}
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

    class Meta:
        model = Story
        fields = ['media_file', 'caption', 'background']

    def validate(self, attrs):
        media_file = attrs.get('media_file')
        caption = (attrs.get('caption') or '').strip()

        if not media_file and not caption:
            raise serializers.ValidationError("Please provide a photo, video, or type text for your story.")

        if media_file:
            if media_file.size > self.MAX_FILE_SIZE:
                raise serializers.ValidationError("File size exceeds maximum 25 MB limit for stories.")

            ext = os.path.splitext(media_file.name)[1].lower()
            if ext not in self.ALLOWED_IMAGE_EXTS and ext not in self.ALLOWED_VIDEO_EXTS:
                raise serializers.ValidationError(
                    f"Unsupported file format '{ext}'. Allowed formats: JPG, PNG, WEBP, GIF, MP4, MOV, WEBM."
                )
        return attrs

    def create(self, validated_data):
        file_obj = validated_data.get('media_file')
        caption = (validated_data.get('caption') or '').strip()
        background = validated_data.get('background', 'gradient-blue') or 'gradient-blue'

        if file_obj:
            ext = os.path.splitext(file_obj.name)[1].lower()
            media_type = 'VIDEO' if ext in self.ALLOWED_VIDEO_EXTS else 'IMAGE'
        else:
            media_type = 'TEXT'

        story = Story.objects.create(
            author=self.context['request'].user,
            media_file=file_obj,
            media_type=media_type,
            caption=caption,
            background=background,
        )
        return story

