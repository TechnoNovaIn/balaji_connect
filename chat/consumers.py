import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .models import Conversation, Message


class DummyWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')

        # Authentication check
        if not self.user or not self.user.is_authenticated or not getattr(self.user, 'is_active', False):
            await self.close(code=4401)
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f"chat_{self.conversation_id}"

        # Verification: user must be participant of conversation
        is_participant = await self.is_user_participant()
        if not is_participant:
            await self.close(code=4403)
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except Exception:
            return

        message_type = data.get('type', 'message')
        if message_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
            return

        content = data.get('message', '').strip()
        shared_post_id = data.get('shared_post_id')

        if not content and not shared_post_id:
            return

        if len(content) > 5000:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'detail': 'Message exceeds 5,000 character limit.'
            }))
            return

        # Persist message in PostgreSQL
        msg_obj = await self.save_message(content, shared_post_id=shared_post_id)

        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': msg_obj['id'],
                'conversation_id': self.conversation_id,
                'sender_id': msg_obj['sender_id'],
                'sender_employee_id': msg_obj['sender_employee_id'],
                'sender_name': msg_obj['sender_name'],
                'sender_avatar': msg_obj['sender_avatar'],
                'content': msg_obj['content'],
                'shared_post': msg_obj.get('shared_post'),
                'created_at': msg_obj['created_at'],
            }
        )

    async def chat_message(self, event):
        # Forward group message to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event['id'],
            'conversation_id': event['conversation_id'],
            'sender_id': event['sender_id'],
            'sender_employee_id': event['sender_employee_id'],
            'sender_name': event['sender_name'],
            'sender_avatar': event['sender_avatar'],
            'content': event['content'],
            'shared_post': event.get('shared_post'),
            'created_at': event['created_at'],
        }))

    @database_sync_to_async
    def is_user_participant(self):
        try:
            return Conversation.objects.filter(
                id=self.conversation_id,
                participants=self.user
            ).exists()
        except Exception:
            return False

    @database_sync_to_async
    def save_message(self, content, shared_post_id=None):
        conv = Conversation.objects.get(id=self.conversation_id)
        shared_post = None
        if shared_post_id:
            from posts.models import Post
            shared_post = Post.objects.filter(id=shared_post_id, is_deleted=False).first()

        msg = Message.objects.create(
            conversation=conv,
            sender=self.user,
            content=content,
            shared_post=shared_post
        )
        conv.save()  # Touch updated_at

        from .serializers import MessageSerializer
        serialized = MessageSerializer(msg).data

        return {
            'id': msg.id,
            'sender_id': self.user.id,
            'sender_employee_id': self.user.employee_id,
            'sender_name': self.user.full_name,
            'sender_avatar': getattr(self.user, 'avatar_url', ''),
            'content': msg.content,
            'shared_post': serialized.get('shared_post'),
            'created_at': msg.created_at.isoformat(),
        }

