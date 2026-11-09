import io
from PIL import Image
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import Employee, Department
from .models import MediaAttachment
from .services import get_storage_service, LocalStorageDriver, GoogleDriveStorageDriver
from .services.base import StorageAuthenticationException

def create_test_image(format='PNG', size=(100, 100), color='blue'):
    file = io.BytesIO()
    img = Image.new('RGB', size, color=color)
    img.save(file, format=format)
    file.name = f'test.{format.lower()}'
    file.seek(0)
    return file


class MediaVaultTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dept = Department.objects.create(name="Operations", code="OPS")
        self.employee = Employee.objects.create_user(
            employee_id="BT-2001",
            first_name="Karan",
            last_name="Singh",
            password="EmployeePassword123!",
            department=self.dept
        )

    def test_upload_image_success(self):
        self.client.force_authenticate(user=self.employee)
        img_file = create_test_image('PNG')
        
        url = reverse('media-upload')
        response = self.client.post(url, {'file': img_file}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertIn('view_url', response.data)
        self.assertEqual(response.data['file_type'], 'IMAGE')

        # Check DB record
        attachment = MediaAttachment.objects.get(id=response.data['id'])
        self.assertEqual(attachment.uploader, self.employee)
        self.assertFalse(attachment.is_deleted)

    def test_media_stream_authorized_access(self):
        self.client.force_authenticate(user=self.employee)
        img_file = create_test_image('PNG')
        
        # Upload
        up_resp = self.client.post(reverse('media-upload'), {'file': img_file}, format='multipart')
        media_id = up_resp.data['id']

        # Stream
        stream_url = reverse('media-view', kwargs={'pk': media_id})
        stream_resp = self.client.get(stream_url)
        
        self.assertEqual(stream_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(stream_resp.get('Content-Type'), 'image/png')
        self.assertEqual(stream_resp.get('X-Content-Type-Options'), 'nosniff')

    def test_media_stream_unauthorized_access_denied(self):
        self.client.force_authenticate(user=self.employee)
        img_file = create_test_image('PNG')
        up_resp = self.client.post(reverse('media-upload'), {'file': img_file}, format='multipart')
        media_id = up_resp.data['id']

        # Unauthenticated request
        self.client.logout()
        stream_url = reverse('media-view', kwargs={'pk': media_id})
        stream_resp = self.client.get(stream_url)
        self.assertIn(stream_resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_deactivated_employee_denied_media_access(self):
        self.client.force_authenticate(user=self.employee)
        img_file = create_test_image('PNG')
        up_resp = self.client.post(reverse('media-upload'), {'file': img_file}, format='multipart')
        media_id = up_resp.data['id']

        # Deactivate employee
        self.employee.is_active = False
        self.employee.save()

        stream_url = reverse('media-view', kwargs={'pk': media_id})
        stream_resp = self.client.get(stream_url)
        self.assertEqual(stream_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_retry_deduplication(self):
        self.client.force_authenticate(user=self.employee)
        img_file1 = create_test_image('PNG', color='red')
        img_file2 = create_test_image('PNG', color='red')

        url = reverse('media-upload')
        r1 = self.client.post(url, {'file': img_file1}, format='multipart')
        r2 = self.client.post(url, {'file': img_file2}, format='multipart')

        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        # Should return same media id without duplicate database row
        self.assertEqual(r1.data['id'], r2.data['id'])
        self.assertEqual(MediaAttachment.objects.count(), 1)

    def test_invalid_corrupt_file_rejected(self):
        self.client.force_authenticate(user=self.employee)
        fake_file = io.BytesIO(b'not a valid image content')
        fake_file.name = 'fake.png'
        fake_file.content_type = 'image/png'

        url = reverse('media-upload')
        response = self.client.post(url, {'file': fake_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_google_drive_driver_unconfigured_exception(self):
        # When unconfigured, it should raise a clear StorageAuthenticationException
        driver = GoogleDriveStorageDriver(client_id='', client_secret='', refresh_token='')
        with self.assertRaises(StorageAuthenticationException):
            driver.upload_file(io.BytesIO(b'test'), 'test.txt', 'text/plain', 4)
