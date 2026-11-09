from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Employee, Department
from posts.models import Post, Comment
from media_vault.models import MediaAttachment
from .models import ContentReport, AuditLog

class ModerationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dept = Department.objects.create(name="Human Resources", code="HR")

        self.employee1 = Employee.objects.create_user(
            employee_id="BT-5001",
            first_name="Meena",
            last_name="Rao",
            password="Password123!",
            department=self.dept
        )

        self.employee2 = Employee.objects.create_user(
            employee_id="BT-5002",
            first_name="Dev",
            last_name="Anand",
            password="Password123!",
            department=self.dept
        )

        self.admin = Employee.objects.create_superuser(
            employee_id="BT-0001",
            first_name="Admin",
            last_name="Lead",
            password="AdminPassword123!",
            role=Employee.Role.ADMIN
        )

        self.post = Post.objects.create(author=self.employee2, content="Questionable post text")

    def test_employee_can_report_post(self):
        self.client.force_authenticate(user=self.employee1)
        url = reverse('report-list')
        response = self.client.post(url, {
            'post': self.post.id,
            'reason': 'INAPPROPRIATE',
            'description': 'Violates company safety guideline disclosure.'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ContentReport.objects.count(), 1)
        report = ContentReport.objects.first()
        self.assertEqual(report.reporter, self.employee1)
        self.assertEqual(report.status, 'PENDING')

    def test_regular_employee_cannot_list_reports(self):
        self.client.force_authenticate(user=self.employee1)
        url = reverse('report-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_reports_with_media_attachments(self):
        attachment = MediaAttachment.objects.create(
            uploader=self.employee2,
            storage_provider='local',
            storage_file_id='test-file-123.jpg',
            original_filename='photo.jpg',
            file_type='IMAGE',
            mime_type='image/jpeg',
            file_size_bytes=1024,
            file_hash='abc123hash'
        )
        self.post.media_attachments.add(attachment)

        ContentReport.objects.create(
            reporter=self.employee1,
            post=self.post,
            reason='INAPPROPRIATE',
            description='Report with media attachment'
        )

        self.client.force_authenticate(user=self.admin)
        url = reverse('report-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        media_urls = response.data['results'][0]['target_summary']['media_urls']
        self.assertEqual(len(media_urls), 1)
        self.assertIn(f'/api/v1/media/{attachment.pk}/view/', media_urls[0])

    def test_admin_can_review_and_remove_reported_post(self):
        report = ContentReport.objects.create(
            reporter=self.employee1,
            post=self.post,
            reason='INAPPROPRIATE',
            description='Inappropriate'
        )

        self.client.force_authenticate(user=self.admin)
        url = reverse('report-review', kwargs={'pk': report.pk})
        response = self.client.post(url, {
            'status': 'RESOLVED',
            'remove_content': True,
            'admin_notes': 'Removed by admin for violating policies.'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, 'RESOLVED')
        self.assertEqual(report.reviewed_by, self.admin)

        # Offending post is removed
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_deleted)

        # Audit log is created
        self.assertTrue(AuditLog.objects.filter(action='MODERATION_REMOVE_POST').exists())

    def test_regular_employee_cannot_access_audit_logs(self):
        self.client.force_authenticate(user=self.employee1)
        url = reverse('audit-log-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_notified_on_report_creation(self):
        from notifications.models import Notification
        self.client.force_authenticate(user=self.employee1)
        url = reverse('report-list')
        response = self.client.post(url, {
            'post': self.post.id,
            'reason': 'HARASSMENT',
            'description': 'Disrespectful language toward coworker.'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Admin received a notification
        notif = Notification.objects.filter(recipient=self.admin, notification_type=Notification.NotificationType.SYSTEM).first()
        self.assertIsNotNone(notif)
        self.assertIn("flagged", notif.title.lower())
        self.assertIn(f"Post #{self.post.id}", notif.message)

    def test_admin_can_archive_post_via_moderation(self):
        report = ContentReport.objects.create(
            reporter=self.employee1,
            post=self.post,
            reason='SPAM',
            description='Duplicate marketing spam.'
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse('report-review', kwargs={'pk': report.pk})
        response = self.client.post(url, {
            'status': 'RESOLVED',
            'archive_content': True,
            'admin_notes': 'Archived by administrator.'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_archived)
        self.assertFalse(self.post.is_deleted)

    def test_admin_post_archive_and_unarchive_actions(self):
        self.client.force_authenticate(user=self.admin)
        archive_url = reverse('post-archive', kwargs={'pk': self.post.pk})
        resp = self.client.post(archive_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_archived)

        # Normal feed hides archived post
        feed_url = reverse('post-list')
        resp_feed = self.client.get(feed_url)
        feed_ids = [p['id'] for p in resp_feed.data['results']]
        self.assertNotIn(self.post.id, feed_ids)

        # Admin archive query shows archived post
        resp_archived = self.client.get(f"{feed_url}?archived=true")
        archived_ids = [p['id'] for p in resp_archived.data['results']]
        self.assertIn(self.post.id, archived_ids)

        # Admin unarchive
        unarchive_url = reverse('post-unarchive', kwargs={'pk': self.post.pk})
        resp_unarchive = self.client.post(unarchive_url)
        self.assertEqual(resp_unarchive.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_archived)
