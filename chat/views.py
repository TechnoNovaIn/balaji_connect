from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, views, permissions
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from accounts.models import Employee
from accounts.permissions import IsActiveEmployee
from posts.models import Post
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer


def broadcast_chat_message(message, request=None):
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            serialized_data = MessageSerializer(message, context={'request': request}).data
            payload = {
                'type': 'chat_message',
                'id': message.id,
                'conversation_id': message.conversation_id,
                'sender_id': message.sender_id,
                'sender_employee_id': message.sender.employee_id,
                'sender_name': message.sender.full_name,
                'sender_avatar': message.sender.avatar_url,
                'content': message.content,
                'shared_post': serialized_data.get('shared_post'),
                'created_at': message.created_at.isoformat(),
            }
            async_to_sync(channel_layer.group_send)(
                f"chat_{message.conversation_id}",
                payload
            )
    except Exception:
        pass


class ConversationListCreateView(views.APIView):
    permission_classes = [IsActiveEmployee]

    def get(self, request):
        conversations = (
            Conversation.objects.filter(participants=request.user)
            .prefetch_related('participants', 'messages')
            .order_by('-updated_at')
        )
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        recipient_id = request.data.get('recipient_id')
        recipient_emp_id = request.data.get('employee_id')

        recipient = None
        if recipient_id:
            recipient = Employee.objects.filter(id=recipient_id, is_active=True).first()
        elif recipient_emp_id:
            recipient = Employee.objects.filter(
                Q(employee_id__iexact=recipient_emp_id) | Q(username__iexact=recipient_emp_id),
                is_active=True
            ).first()

        if not recipient:
            return Response(
                {'detail': 'Recipient employee not found or is inactive.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if recipient.id == request.user.id:
            return Response(
                {'detail': 'You cannot initiate a private conversation with yourself.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find existing 1-on-1 conversation
        existing = Conversation.objects.filter(participants=request.user).filter(participants=recipient).first()
        if existing:
            serializer = ConversationSerializer(existing, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Create new conversation
        with transaction.atomic():
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, recipient)

        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConversationDetailView(views.APIView):
    permission_classes = [IsActiveEmployee]

    def get_conversation(self, conversation_id, user):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if not conversation.participants.filter(id=user.id).exists():
            return None
        return conversation

    def get(self, request, pk):
        conversation = self.get_conversation(pk, request.user)
        if not conversation:
            return Response(
                {'detail': 'You do not have permission to access this private conversation.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data)


class MessageListCreateView(views.APIView):
    permission_classes = [IsActiveEmployee]

    def get_conversation(self, conversation_id, user):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if not conversation.participants.filter(id=user.id).exists():
            return None
        return conversation

    def get(self, request, conversation_id):
        conversation = self.get_conversation(conversation_id, request.user)
        if not conversation:
            return Response(
                {'detail': 'You do not have permission to access these messages.'},
                status=status.HTTP_403_FORBIDDEN
            )

        messages = conversation.messages.select_related('sender', 'shared_post', 'shared_post__author').prefetch_related('shared_post__media_attachments').order_by('created_at')
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, conversation_id):
        conversation = self.get_conversation(conversation_id, request.user)
        if not conversation:
            return Response(
                {'detail': 'You do not have permission to post messages here.'},
                status=status.HTTP_403_FORBIDDEN
            )

        content = request.data.get('content', '').strip()
        shared_post_id = request.data.get('shared_post_id')
        shared_post = None

        if shared_post_id:
            shared_post = Post.objects.filter(id=shared_post_id, is_deleted=False).first()
            if not shared_post:
                return Response(
                    {'detail': 'The selected post is not available to share.'},
                    status=status.HTTP_404_NOT_FOUND
                )

        if not content and not shared_post:
            return Response(
                {'detail': 'Message content or a shared post is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(content) > 5000:
            return Response(
                {'detail': 'Message content exceeds the 5,000 character limit.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                shared_post=shared_post,
                content=content
            )
            conversation.save()  # Updates conversation.updated_at

        broadcast_chat_message(message, request=request)

        serializer = MessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SharePostToDirectMessageView(views.APIView):
    permission_classes = [IsActiveEmployee]

    def post(self, request):
        post_id = request.data.get('post_id')
        recipient_ids = request.data.get('recipient_ids', [])
        note = request.data.get('message', '').strip()

        if not post_id:
            return Response({'detail': 'post_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        post = get_object_or_404(Post, id=post_id, is_deleted=False)

        if not recipient_ids or not isinstance(recipient_ids, list):
            return Response(
                {'detail': 'Please select at least one employee to share this post with.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filter valid active recipients excluding sender
        recipients = list(Employee.objects.filter(
            id__in=recipient_ids,
            is_active=True
        ).exclude(id=request.user.id))

        if not recipients:
            return Response(
                {'detail': 'No valid recipient employees found.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_messages = []
        with transaction.atomic():
            for recipient in recipients:
                # Find or create 1-on-1 conversation
                conv = Conversation.objects.filter(participants=request.user).filter(participants=recipient).first()
                if not conv:
                    conv = Conversation.objects.create()
                    conv.participants.add(request.user, recipient)

                msg = Message.objects.create(
                    conversation=conv,
                    sender=request.user,
                    shared_post=post,
                    content=note
                )
                conv.save()
                created_messages.append(msg)

        # Broadcast each message to channel layer
        for msg in created_messages:
            broadcast_chat_message(msg, request=request)

        return Response({
            'detail': f'Post shared with {len(created_messages)} employee(s) successfully.',
            'shared_count': len(created_messages),
        }, status=status.HTTP_201_CREATED)


class MarkConversationReadView(views.APIView):
    permission_classes = [IsActiveEmployee]

    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {'detail': 'You do not have permission to modify this conversation.'},
                status=status.HTTP_403_FORBIDDEN
            )

        unread = conversation.messages.exclude(sender=request.user).filter(is_read=False)
        updated_count = unread.update(is_read=True)
        return Response({'marked_read': updated_count}, status=status.HTTP_200_OK)
