from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Employee, Department
from posts.models import Post
from .models import Notification

class NotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dept = Department.objects.create(name="Fleet", code="FLT")

        self.author = Employee.objects.create_user(
            employee_id="BT-4001",
            first_name="Vikram",
            last_name="Reddy",
            password="Password123!",
            department=self.dept
        )

        self.actor = Employee.objects.create_user(
            employee_id="BT-4002",
            first_name="Sunil",
            last_name="Gowda",
            password="Password123!",
            department=self.dept
        )

        self.post = Post.objects.create(author=self.author, content="Fleet inspection complete.")

    def test_like_generates_notification(self):
        self.client.force_authenticate(user=self.actor)
        self.client.post(reverse('post-toggle-reaction', kwargs={'pk': self.post.pk}))

        # Author receives notification
        notif = Notification.objects.filter(recipient=self.author).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.notification_type, Notification.NotificationType.REACTION)
        self.assertEqual(notif.sender, self.actor)
        self.assertFalse(notif.is_read)

    def test_self_like_does_not_generate_notification(self):
        self.client.force_authenticate(user=self.author)
        self.client.post(reverse('post-toggle-reaction', kwargs={'pk': self.post.pk}))
        self.assertEqual(Notification.objects.filter(recipient=self.author).count(), 0)

    def test_comment_generates_notification(self):
        self.client.force_authenticate(user=self.actor)
        self.client.post(
            reverse('post-comments', kwargs={'pk': self.post.pk}),
            {'content': 'Looks good to go!'},
            format='json'
        )
        notif = Notification.objects.filter(recipient=self.author, notification_type=Notification.NotificationType.COMMENT).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.sender, self.actor)

    def test_notification_unread_count_and_mark_read(self):
        Notification.objects.create(
            recipient=self.author,
            sender=self.actor,
            title="Update",
            message="Test notification",
            is_read=False
        )

        self.client.force_authenticate(user=self.author)
        count_resp = self.client.get(reverse('notification-unread-count'))
        self.assertEqual(count_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(count_resp.data['unread_count'], 1)

        # Mark all read
        mark_resp = self.client.post(reverse('notification-mark-all-read'))
        self.assertEqual(mark_resp.status_code, status.HTTP_200_OK)

        count_resp2 = self.client.get(reverse('notification-unread-count'))
        self.assertEqual(count_resp2.data['unread_count'], 0)
