from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest
from rest_framework import status, viewsets, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsActiveEmployee, IsOwnerOrAdmin, IsAdminRole
from .models import Post, PostReaction, Comment, CommentReaction
from .serializers import PostSerializer, CommentSerializer, PostReactionSerializer

class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsActiveEmployee(), IsOwnerOrAdmin()]
        if self.action in ['archive', 'unarchive']:
            return [IsAdminRole()]
        return [IsActiveEmployee()]

    def get_queryset(self):
        user = self.request.user
        archived_filter = self.request.query_params.get('archived')
        is_archived_query = str(archived_filter).lower() in ['true', '1']

        if is_archived_query:
            if user.is_authenticated and (getattr(user, 'role', None) == 'ADMIN' or getattr(user, 'is_administrator', False)):
                qs = Post.objects.filter(is_deleted=False, is_archived=True)
            else:
                qs = Post.objects.none()
        else:
            qs = Post.objects.filter(is_deleted=False, is_archived=False)

        qs = qs.select_related(
            'author',
            'author__department'
        ).prefetch_related(
            'media_attachments'
        ).order_by('-created_at', '-id')

        # Filter by author if query parameter provided (e.g. employee profile view)
        author_id = self.request.query_params.get('author')
        if author_id:
            qs = qs.filter(author_id=author_id)

        return qs

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @action(detail=True, methods=['post'], permission_classes=[IsAdminRole])
    def archive(self, request, pk=None):
        # Allow archiving an active post
        post = Post.objects.filter(pk=pk, is_deleted=False).first()
        if not post:
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        post.is_archived = True
        post.save(update_fields=['is_archived'])

        try:
            from moderation.models import AuditLog
            AuditLog.objects.create(
                actor=request.user,
                action='POST_ARCHIVE',
                target_model='Post',
                target_id=str(post.id),
                details={'content_snippet': post.content[:80] if post.content else '[Media]'},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
        except Exception:
            pass

        return Response({
            'status': 'archived',
            'id': post.id,
            'message': f"Post #{post.id} archived successfully."
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminRole])
    def unarchive(self, request, pk=None):
        post = Post.objects.filter(pk=pk, is_deleted=False).first()
        if not post:
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

        post.is_archived = False
        post.save(update_fields=['is_archived'])

        try:
            from moderation.models import AuditLog
            AuditLog.objects.create(
                actor=request.user,
                action='POST_UNARCHIVE',
                target_model='Post',
                target_id=str(post.id),
                details={'content_snippet': post.content[:80] if post.content else '[Media]'},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
        except Exception:
            pass

        return Response({
            'status': 'unarchived',
            'id': post.id,
            'message': f"Post #{post.id} restored to feed."
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsActiveEmployee])
    def toggle_reaction(self, request, pk=None):
        post = self.get_object()
        user = request.user
        req_type = request.data.get('reaction_type', 'LIKE')
        if req_type not in PostReaction.ReactionType.values:
            req_type = PostReaction.ReactionType.LIKE

        with transaction.atomic():
            reaction = PostReaction.objects.filter(
                post=post,
                user=user
            ).first()

            if reaction:
                if reaction.reaction_type == req_type:
                    # Same reaction clicked again -> remove reaction (toggle off)
                    reaction.delete()
                    Post.objects.filter(pk=post.pk).update(like_count=Greatest(F('like_count') - 1, 0))
                    liked = False
                    user_reaction = None
                else:
                    # Different reaction clicked -> switch reaction type
                    reaction.reaction_type = req_type
                    reaction.save(update_fields=['reaction_type'])
                    liked = True
                    user_reaction = req_type
            else:
                # New reaction
                PostReaction.objects.create(
                    post=post,
                    user=user,
                    reaction_type=req_type
                )
                Post.objects.filter(pk=post.pk).update(like_count=F('like_count') + 1)
                liked = True
                user_reaction = req_type

                # Notify author if not self-reaction
                if post.author != user:
                    try:
                        from notifications.models import Notification
                        emoji_map = {
                            'LIKE': '👍', 'LOVE': '❤️', 'HAHA': '😂',
                            'WOW': '😮', 'SAD': '😢', 'ANGRY': '😡'
                        }
                        Notification.objects.create(
                            recipient=post.author,
                            sender=user,
                            notification_type=Notification.NotificationType.REACTION,
                            target_post=post,
                            title="New Reaction",
                            message=f"{user.full_name} reacted {emoji_map.get(req_type, '')} to your post."
                        )
                    except Exception:
                        pass

        post.refresh_from_db(fields=['like_count'])
        return Response({
            'liked': liked,
            'like_count': post.like_count,
            'user_reaction': user_reaction,
            'reaction_type': user_reaction,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[IsActiveEmployee])
    def reactions(self, request, pk=None):
        post = self.get_object()
        reactions = post.reactions.select_related('user', 'user__department').order_by('-created_at')

        from django.db.models import Count
        breakdown = dict(
            post.reactions.values('reaction_type')
            .annotate(total=Count('id'))
            .values_list('reaction_type', 'total')
        )

        type_filter = request.query_params.get('type')
        if type_filter and type_filter.upper() != 'ALL':
            reactions = reactions.filter(reaction_type=type_filter.upper())

        if request.query_params.get('all') == 'true':
            serializer = PostReactionSerializer(reactions, many=True, context={'request': request})
            return Response({
                'count': reactions.count(),
                'breakdown': breakdown,
                'results': serializer.data
            })

        page = self.paginate_queryset(reactions)
        if page is not None:
            serializer = PostReactionSerializer(page, many=True, context={'request': request})
            resp = self.get_paginated_response(serializer.data)
            resp.data['breakdown'] = breakdown
            return resp

        serializer = PostReactionSerializer(reactions, many=True, context={'request': request})
        return Response({
            'count': reactions.count(),
            'breakdown': breakdown,
            'results': serializer.data
        })

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsActiveEmployee])
    def comments(self, request, pk=None):
        post = self.get_object()

        if request.method == 'GET':
            comments = post.comments.filter(is_deleted=False).select_related(
                'author',
                'author__department'
            ).order_by('created_at')
            page = self.paginate_queryset(comments)
            if page is not None:
                serializer = CommentSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            serializer = CommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)

        # POST comment
        serializer = CommentSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            comment = serializer.save(author=request.user, post=post)
            Post.objects.filter(pk=post.pk).update(comment_count=F('comment_count') + 1)

            # Trigger notification if not self-comment
            if post.author != request.user:
                try:
                    from notifications.models import Notification
                    Notification.objects.create(
                        recipient=post.author,
                        sender=request.user,
                        notification_type=Notification.NotificationType.COMMENT,
                        target_post=post,
                        target_comment=comment,
                        title="New Comment",
                        message=f"{request.user.full_name} commented on your post."
                    )
                except Exception:
                    pass

        post.refresh_from_db(fields=['comment_count'])
        output = CommentSerializer(comment, context={'request': request}).data
        return Response(output, status=status.HTTP_201_CREATED)


class CommentViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    queryset = Comment.objects.filter(is_deleted=False)
    serializer_class = CommentSerializer
    permission_classes = [IsActiveEmployee, IsOwnerOrAdmin]

    def get_queryset(self):
        qs = Comment.objects.filter(is_deleted=False).select_related(
            'author',
            'author__department',
            'post'
        ).order_by('-created_at')

        author_id = self.request.query_params.get('author')
        if author_id:
            qs = qs.filter(author_id=author_id)

        post_id = self.request.query_params.get('post')
        if post_id:
            qs = qs.filter(post_id=post_id)

        return qs

    def partial_update(self, request, pk=None):
        comment = self.get_object()
        serializer = CommentSerializer(
            comment,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        comment = self.get_object()
        with transaction.atomic():
            comment.is_deleted = True
            comment.save(update_fields=['is_deleted'])
            Post.objects.filter(pk=comment.post_id).update(comment_count=Greatest(F('comment_count') - 1, 0))
        return Response({'detail': 'Comment deleted successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsActiveEmployee])
    def toggle_reaction(self, request, pk=None):
        comment = self.get_object()
        user = request.user
        req_type = request.data.get('reaction_type', 'LIKE').upper()
        if req_type not in CommentReaction.ReactionType.values:
            req_type = 'LIKE'

        with transaction.atomic():
            reaction = CommentReaction.objects.filter(comment=comment, user=user).first()
            if reaction:
                if reaction.reaction_type == req_type:
                    reaction.delete()
                    Comment.objects.filter(pk=comment.pk).update(like_count=Greatest(F('like_count') - 1, 0))
                    liked = False
                    user_reaction = None
                else:
                    reaction.reaction_type = req_type
                    reaction.save(update_fields=['reaction_type'])
                    liked = True
                    user_reaction = req_type
            else:
                CommentReaction.objects.create(comment=comment, user=user, reaction_type=req_type)
                Comment.objects.filter(pk=comment.pk).update(like_count=F('like_count') + 1)
                liked = True
                user_reaction = req_type

        comment.refresh_from_db(fields=['like_count'])
        return Response({
            'liked': liked,
            'like_count': comment.like_count,
            'user_reaction': user_reaction,
            'reaction_type': user_reaction
        }, status=status.HTTP_200_OK)
