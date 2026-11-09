from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from channels.testing import WebsocketCommunicator

from accounts.models import Employee, Department
from chat.models import Conversation, Message
from chat.consumers import ChatConsumer


class ChatDirectMessagingTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Fleet", code="FLT")

        self.user_a = Employee.objects.create_user(
            employee_id="BT-2001",
            username="usera",
            email="usera@balajitransports.internal",
            first_name="Alice",
            last_name="Sharma",
            password="Password123!",
            department=self.dept,
            role=Employee.Role.EMPLOYEE
        )

        self.user_b = Employee.objects.create_user(
            employee_id="BT-2002",
            username="userb",
            email="userb@balajitransports.internal",
            first_name="Bob",
            last_name="Verma",
            password="Password123!",
            department=self.dept,
            role=Employee.Role.EMPLOYEE
        )

        self.user_c = Employee.objects.create_user(
            employee_id="BT-2003",
            username="userc",
            email="userc@balajitransports.internal",
            first_name="Charlie",
            last_name="Patel",
            password="Password123!",
            department=self.dept,
            role=Employee.Role.EMPLOYEE
        )

        self.client_a = APIClient()
        self.client_a.force_authenticate(user=self.user_a)

        self.client_b = APIClient()
        self.client_b.force_authenticate(user=self.user_b)

        self.client_c = APIClient()
        self.client_c.force_authenticate(user=self.user_c)

    def test_start_conversation_between_two_users(self):
        url = reverse('chat:conversation-list-create')
        response = self.client_a.post(url, {'recipient_id': self.user_b.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        conv_id = response.data['id']

        # Calling again returns existing conversation
        response2 = self.client_a.post(url, {'recipient_id': self.user_b.id}, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data['id'], conv_id)

    def test_cannot_chat_with_oneself(self):
        url = reverse('chat:conversation-list-create')
        response = self.client_a.post(url, {'recipient_id': self.user_a.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_and_retrieve_messages_chronological(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user_a, self.user_b)

        url = reverse('chat:message-list-create', kwargs={'conversation_id': conv.id})

        # Alice sends message 1
        resp1 = self.client_a.post(url, {'content': 'Hello Bob, is Truck #14 ready?'}, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp1.data['content'], 'Hello Bob, is Truck #14 ready?')
        self.assertTrue(resp1.data['is_mine'])

        # Bob sends message 2
        resp2 = self.client_b.post(url, {'content': 'Yes Alice, maintenance completed.'}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp2.data['is_mine'])

        # Alice retrieves history
        history_resp = self.client_a.get(url)
        self.assertEqual(history_resp.status_code, status.HTTP_200_OK)
        messages = history_resp.data
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]['content'], 'Hello Bob, is Truck #14 ready?')
        self.assertTrue(messages[0]['is_mine'])
        self.assertEqual(messages[1]['content'], 'Yes Alice, maintenance completed.')
        self.assertFalse(messages[1]['is_mine'])

    def test_strict_privacy_third_party_blocked(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user_a, self.user_b)

        Message.objects.create(conversation=conv, sender=self.user_a, content="Confidential route data")

        # Charlie (user_c) tries to read messages
        url_msgs = reverse('chat:message-list-create', kwargs={'conversation_id': conv.id})
        resp_c_read = self.client_c.get(url_msgs)
        self.assertEqual(resp_c_read.status_code, status.HTTP_403_FORBIDDEN)

        # Charlie tries to send message
        resp_c_send = self.client_c.post(url_msgs, {'content': 'I am spying!'}, format='json')
        self.assertEqual(resp_c_send.status_code, status.HTTP_403_FORBIDDEN)

        # Charlie tries to view conversation detail
        url_conv = reverse('chat:conversation-detail', kwargs={'pk': conv.id})
        resp_c_conv = self.client_c.get(url_conv)
        self.assertEqual(resp_c_conv.status_code, status.HTTP_403_FORBIDDEN)

    def test_mark_conversation_read(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user_a, self.user_b)

        msg = Message.objects.create(conversation=conv, sender=self.user_b, content="Unread message")
        self.assertFalse(msg.is_read)

        url_read = reverse('chat:conversation-mark-read', kwargs={'conversation_id': conv.id})
        resp = self.client_a.post(url_read)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        msg.refresh_from_db()
        self.assertTrue(msg.is_read)

    async def test_websocket_consumer_participant_can_connect_and_exchange(self):
        conv = await Conversation.objects.acreate()
        await conv.participants.aadd(self.user_a, self.user_b)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{conv.id}/"
        )
        communicator.scope['user'] = self.user_a
        communicator.scope['url_route'] = {'kwargs': {'conversation_id': str(conv.id)}}

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send a message
        await communicator.send_json_to({
            'type': 'message',
            'message': 'Real-time test message'
        })

        # Receive broadcast
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'message')
        self.assertEqual(response['content'], 'Real-time test message')
        self.assertEqual(response['sender_employee_id'], self.user_a.employee_id)

        await communicator.disconnect()

    async def test_websocket_consumer_non_participant_rejected(self):
        conv = await Conversation.objects.acreate()
        await conv.participants.aadd(self.user_a, self.user_b)

        # User C tries to connect
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{conv.id}/"
        )
        communicator.scope['user'] = self.user_c
        communicator.scope['url_route'] = {'kwargs': {'conversation_id': str(conv.id)}}

        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)


    def test_share_post_to_direct_message_multiple_recipients(self):
        from posts.models import Post
        post = Post.objects.create(author=self.user_a, content="Important logistics update for highway routes.")

        url = reverse('chat:share-post')
        payload = {
            'post_id': post.id,
            'recipient_ids': [self.user_b.id, self.user_c.id],
            'message': 'Please review this route plan.'
        }
        response = self.client_a.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['shared_count'], 2)

        # Verify Bob's conversation with Alice contains the shared post
        conv_b = Conversation.objects.filter(participants=self.user_a).filter(participants=self.user_b).first()
        self.assertIsNotNone(conv_b)
        msg_b = conv_b.messages.first()
        self.assertEqual(msg_b.shared_post, post)
        self.assertEqual(msg_b.content, 'Please review this route plan.')
        self.assertEqual(msg_b.sender, self.user_a)

        # Retrieve messages as Bob and verify shared_post preview structure
        msgs_url = reverse('chat:message-list-create', kwargs={'conversation_id': conv_b.id})
        b_history = self.client_b.get(msgs_url)
        self.assertEqual(b_history.status_code, status.HTTP_200_OK)
        shared_preview = b_history.data[0]['shared_post']
        self.assertIsNotNone(shared_preview)
        self.assertTrue(shared_preview['is_available'])
        self.assertEqual(shared_preview['id'], post.id)
        self.assertEqual(shared_preview['author_name'], self.user_a.full_name)
        self.assertEqual(shared_preview['content'], post.content)

    def test_share_post_deleted_post_gracefully_handled(self):
        from posts.models import Post
        post = Post.objects.create(author=self.user_a, content="Temporary announcement")

        conv = Conversation.objects.create()
        conv.participants.add(self.user_a, self.user_b)
        msg = Message.objects.create(conversation=conv, sender=self.user_a, shared_post=post, content="Check this")

        # Soft delete the post
        post.is_deleted = True
        post.save()

        # Bob views conversation
        msgs_url = reverse('chat:message-list-create', kwargs={'conversation_id': conv.id})
        response = self.client_b.get(msgs_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shared_preview = response.data[0]['shared_post']
        self.assertIsNotNone(shared_preview)
        self.assertFalse(shared_preview['is_available'])
        self.assertIn('no longer available', shared_preview['message'])

    def test_share_nonexistent_or_deleted_post_rejected(self):
        url = reverse('chat:share-post')
        response = self.client_a.post(url, {'post_id': 99999, 'recipient_ids': [self.user_b.id]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_post_empty_recipients_rejected(self):
        from posts.models import Post
        post = Post.objects.create(author=self.user_a, content="Test content")
        url = reverse('chat:share-post')
        response = self.client_a.post(url, {'post_id': post.id, 'recipient_ids': []}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
