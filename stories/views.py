from collections import defaultdict
from django.shortcuts import get_object_or_404
from rest_framework import status, views, permissions
from rest_framework.response import Response
from accounts.permissions import IsActiveEmployee
from .models import Story, StoryView
from .serializers import (
    StoryItemSerializer,
    UserStoryGroupSerializer,
    StoryCreateSerializer,
)


class StoryFeedView(views.APIView):
    """
    GET: List active (non-expired) stories grouped by author.
    POST: Upload a new 12-hour ephemeral story (saved locally on server disk).
    """
    permission_classes = [IsActiveEmployee]

    def get(self, request):
        # 1. Housekeeping: purge any expired stories & disk files older than 12 hours
        Story.objects.purge_expired()

        # 2. Fetch active stories
        active_stories = (
            Story.objects.active()
            .select_related('author')
            .prefetch_related('views')
            .order_by('created_at')
        )

        # 3. Pre-load IDs of stories current user has already viewed
        user_viewed_ids = set(
            StoryView.objects.filter(
                viewer=request.user,
                story__in=active_stories
            ).values_list('story_id', flat=True)
        )

        serializer_context = {
            'request': request,
            'viewed_story_ids': user_viewed_ids,
        }

        # 4. Group stories by author
        grouped = defaultdict(list)
        for story in active_stories:
            grouped[story.author_id].append(story)

        # Build user group objects
        user_groups = []
        my_group = None

        for author_id, stories in grouped.items():
            first_story = stories[0]
            author = first_story.author

            # Has unseen: True if any story in group is not yet viewed by current user (and user is not author)
            has_unseen = any(
                s.id not in user_viewed_ids
                for s in stories
            ) if author_id != request.user.id else False

            serialized_stories = StoryItemSerializer(
                stories, many=True, context=serializer_context
            ).data

            author_obj = {
                'id': author.id,
                'full_name': author.full_name,
                'first_name': author.first_name or author.full_name,
                'avatar_url': author.avatar_url,
                'username': author.username,
            }

            group_data = {
                'author_id': author.id,
                'author_name': author.full_name,
                'author_avatar': author.avatar_url,
                'author': author_obj,
                'has_unseen': has_unseen,
                'stories_count': len(stories),
                'stories': serialized_stories,
            }

            if author_id == request.user.id:
                my_group = group_data
            else:
                user_groups.append(group_data)

        # Sort colleagues: unseen stories first, then seen stories, then by author name
        user_groups.sort(key=lambda g: (not g['has_unseen'], g['author_name'].lower()))

        # If current user has active stories, place them at the very beginning
        response_data = []
        if my_group:
            response_data.append(my_group)
        response_data.extend(user_groups)

        return Response(response_data)

    def post(self, request):
        # Ephemeral story upload (Stored locally in media/stories/, bypassing Google Drive)
        serializer = StoryCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        story = serializer.save()
        data = StoryItemSerializer(story, context={'request': request}).data
        return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StoryRecordViewView(views.APIView):
    """
    POST: Record that the current user viewed this story.
    """
    permission_classes = [IsActiveEmployee]

    def post(self, request, pk):
        story = get_object_or_404(Story.objects.active(), pk=pk)

        # Author viewing their own story doesn't increment viewer list
        if story.author_id != request.user.id:
            StoryView.objects.get_or_create(story=story, viewer=request.user)

        return Response({
            'status': 'success',
            'story_id': story.id,
            'view_count': story.view_count
        })


class StoryDetailView(views.APIView):
    """
    DELETE: Author (or Admin) deletes their story early.
    """
    permission_classes = [IsActiveEmployee]

    def delete(self, request, pk):
        story = get_object_or_404(Story, pk=pk)

        # Only author or staff/admin can delete
        if story.author_id != request.user.id and not request.user.is_staff:
            return Response(
                {'detail': 'You do not have permission to delete this story.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Delete physical file from disk
        try:
            if story.media_file:
                story.media_file.delete(save=False)
        except Exception:
            pass

        story.delete()
        return Response({'status': 'deleted'}, status=status.HTTP_200_OK)
