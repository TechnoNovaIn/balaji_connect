import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import Employee, Department
from stories.models import Story, StoryView


class StoryAPITests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Operations')
        self.user1 = Employee.objects.create_user(
            employee_id='EMP001',
            username='user1',
            email='user1@balaji.com',
            password='Password123!',
            first_name='Ravi',
            last_name='Kumar',
            department=self.dept,
        )
        self.user2 = Employee.objects.create_user(
            employee_id='EMP002',
            username='user2',
            email='user2@balaji.com',
            password='Password123!',
            first_name='Priya',
            last_name='Sharma',
            department=self.dept,
        )
        self.client = APIClient()

    def _create_sample_image(self):
        file = io.BytesIO()
        image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0, 0))
        image.save(file, 'png')
        file.name = 'test_story.png'
        file.seek(0)
        return SimpleUploadedFile(file.name, file.read(), content_type='image/png')

    def test_create_story_success(self):
        self.client.force_authenticate(user=self.user1)
        image = self._create_sample_image()
        response = self.client.post('/api/v1/stories/', {
            'media_file': image,
            'caption': 'Warehouse inspection update'
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Story.objects.count(), 1)
        story = Story.objects.first()
        self.assertEqual(story.author, self.user1)
        self.assertEqual(story.caption, 'Warehouse inspection update')
        self.assertEqual(story.media_type, 'IMAGE')

    def test_story_feed_grouped_by_author(self):
        # user1 uploads a story
        self.client.force_authenticate(user=self.user1)
        image1 = self._create_sample_image()
        self.client.post('/api/v1/stories/', {'media_file': image1, 'caption': 'Story 1'}, format='multipart')

        # user2 views feed
        self.client.force_authenticate(user=self.user2)
        response = self.client.get('/api/v1/stories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        group = response.data[0]
        self.assertEqual(group['author_id'], self.user1.id)
        self.assertIn('author', group)
        self.assertEqual(group['author']['full_name'], 'Ravi Kumar')
        self.assertTrue(group['has_unseen'])

    def test_record_story_view(self):
        self.client.force_authenticate(user=self.user1)
        image = self._create_sample_image()
        res = self.client.post('/api/v1/stories/', {'media_file': image}, format='multipart')
        story_id = res.data['id']

        # user2 records view
        self.client.force_authenticate(user=self.user2)
        view_res = self.client.post(f'/api/v1/stories/{story_id}/view/')
        self.assertEqual(view_res.status_code, status.HTTP_200_OK)
        self.assertEqual(view_res.data['view_count'], 1)
        self.assertEqual(StoryView.objects.count(), 1)

    def test_author_delete_story(self):
        self.client.force_authenticate(user=self.user1)
        image = self._create_sample_image()
        res = self.client.post('/api/v1/stories/', {'media_file': image}, format='multipart')
        story_id = res.data['id']

        # Delete story
        del_res = self.client.delete(f'/api/v1/stories/{story_id}/')
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        self.assertEqual(Story.objects.count(), 0)
