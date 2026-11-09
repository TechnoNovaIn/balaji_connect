import io
from PIL import Image
from datetime import date
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import Employee, Department

class AccountAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dept_ops = Department.objects.create(name="Operations", code="OPS")
        self.dept_it = Department.objects.create(name="Information Technology", code="IT")

        self.admin_user = Employee.objects.create_superuser(
            employee_id="BT-0001",
            first_name="Admin",
            last_name="Balaji",
            password="StrongAdminPassword123!",
            department=self.dept_it,
            role=Employee.Role.ADMIN
        )

        self.employee_user = Employee.objects.create_user(
            employee_id="BT-1001",
            first_name="Ramesh",
            last_name="Kumar",
            password="EmployeePassword123!",
            department=self.dept_ops,
            role=Employee.Role.EMPLOYEE
        )

    def test_login_success(self):
        url = reverse('auth-login')
        response = self.client.post(url, {
            'identifier': 'BT-1001',
            'password': 'EmployeePassword123!',
            'remember_me': True
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('employee', response.data)
        self.assertEqual(response.data['employee']['employee_id'], 'BT-1001')
        self.assertEqual(self.client.session.get_expiry_age(), 86400 * 30)

    def test_login_session_browser_close_when_remember_me_false(self):
        url = reverse('auth-login')
        response = self.client.post(url, {
            'identifier': 'BT-1001',
            'password': 'EmployeePassword123!',
            'remember_me': False
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_login_invalid_credentials(self):
        url = reverse('auth-login')
        response = self.client.post(url, {
            'identifier': 'BT-1001',
            'password': 'WrongPassword999!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deactivated_employee_login_denied(self):
        self.employee_user.is_active = False
        self.employee_user.save()

        url = reverse('auth-login')
        response = self.client.post(url, {
            'identifier': 'BT-1001',
            'password': 'EmployeePassword123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('deactivated', str(response.data))

    def test_regular_employee_cannot_create_employee(self):
        self.client.force_authenticate(user=self.employee_user)
        url = reverse('employee-list')
        response = self.client.post(url, {
            'employee_id': 'BT-1002',
            'first_name': 'Suresh',
            'last_name': 'Verma',
            'password': 'NewPassword123!',
            'department': self.dept_ops.id
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_employee(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('employee-list')
        response = self.client.post(url, {
            'employee_id': 'BT-1002',
            'first_name': 'Suresh',
            'last_name': 'Verma',
            'password': 'NewPassword123!',
            'department': self.dept_ops.id,
            'designation': 'Senior Driver'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Employee.objects.filter(employee_id='BT-1002').exists())

    def test_admin_can_toggle_employee_status(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('employee-toggle-status', kwargs={'pk': self.employee_user.pk})
        
        # Deactivate
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.employee_user.refresh_from_db()
        self.assertFalse(self.employee_user.is_active)

        # Reactivate
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.employee_user.refresh_from_db()
        self.assertTrue(self.employee_user.is_active)

    def test_change_password(self):
        self.client.force_authenticate(user=self.employee_user)
        url = reverse('auth-change-password')
        response = self.client.post(url, {
            'old_password': 'EmployeePassword123!',
            'new_password': 'BrandNewPassword999!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify old password no longer works
        self.client.logout()
        login_url = reverse('auth-login')
        resp_old = self.client.post(login_url, {'identifier': 'BT-1001', 'password': 'EmployeePassword123!'})
        self.assertEqual(resp_old.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify new password works
        resp_new = self.client.post(login_url, {'identifier': 'BT-1001', 'password': 'BrandNewPassword999!'})
        self.assertEqual(resp_new.status_code, status.HTTP_200_OK)

    def test_logout_invalidates_session_and_token(self):
        login_url = reverse('auth-login')
        resp_login = self.client.post(login_url, {
            'identifier': 'BT-1001',
            'password': 'EmployeePassword123!'
        }, format='json')
        self.assertEqual(resp_login.status_code, status.HTTP_200_OK)

        # Call logout
        logout_url = reverse('auth-logout')
        resp_logout = self.client.post(logout_url)
        self.assertEqual(resp_logout.status_code, status.HTTP_200_OK)

        # Session is flushed -> unauthenticated access to auth-me is denied
        me_url = reverse('auth-me')
        resp_me = self.client.get(me_url)
        self.assertIn(resp_me.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_employee_update_profile_own(self):
        self.client.force_authenticate(user=self.employee_user)
        url = reverse('auth-me')
        response = self.client.patch(url, {
            'display_name': 'Ramesh K.',
            'date_of_birth': '1995-08-15',
            'phone_number': '+91 9876543210'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.employee_user.refresh_from_db()
        self.assertEqual(self.employee_user.display_name, 'Ramesh K.')
        self.assertEqual(str(self.employee_user.date_of_birth), '1995-08-15')
        self.assertEqual(self.employee_user.phone_number, '+91 9876543210')
        self.assertEqual(self.employee_user.full_name, 'Ramesh K.')

    def test_employee_clear_date_of_birth(self):
        self.employee_user.date_of_birth = date(1992, 5, 20)
        self.employee_user.save()

        self.client.force_authenticate(user=self.employee_user)
        url = reverse('auth-me')
        response = self.client.patch(url, {'date_of_birth': ''}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.employee_user.refresh_from_db()
        self.assertIsNone(self.employee_user.date_of_birth)

    def test_employee_cannot_modify_protected_fields(self):
        self.client.force_authenticate(user=self.employee_user)
        url = reverse('auth-me')
        response = self.client.patch(url, {
            'role': Employee.Role.ADMIN,
            'employee_id': 'BT-HACK',
            'is_active': False
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.employee_user.refresh_from_db()
        self.assertEqual(self.employee_user.role, Employee.Role.EMPLOYEE)
        self.assertEqual(self.employee_user.employee_id, 'BT-1001')
        self.assertTrue(self.employee_user.is_active)

    def test_employee_cannot_update_other_profile(self):
        self.client.force_authenticate(user=self.employee_user)
        other_user = Employee.objects.create_user(
            employee_id="BT-1005",
            first_name="Other",
            last_name="Person",
            password="Password123!"
        )
        url = reverse('employee-detail', kwargs={'pk': other_user.pk})
        response = self.client.patch(url, {'display_name': 'Hacked'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_birthdays_endpoint_and_privacy(self):
        today = timezone.localdate()
        # Set employee birthday to today
        self.employee_user.date_of_birth = date(1990, today.month, today.day)
        self.employee_user.save()

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('employee-birthdays')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(e['id'] == self.employee_user.id for e in response.data))

        # Strict privacy check: birth year 1990 must NOT appear in output!
        resp_json = str(response.data)
        self.assertNotIn('1990', resp_json)
        self.assertNotIn('date_of_birth', response.data[0])

    def test_avatar_upload_valid_image(self):
        self.client.force_authenticate(user=self.employee_user)
        # Create a small valid in-memory PNG
        file_obj = io.BytesIO()
        image = Image.new('RGB', (100, 100), color='blue')
        image.save(file_obj, format='PNG')
        file_obj.seek(0)

        upload_file = SimpleUploadedFile('my_avatar.png', file_obj.read(), content_type='image/png')
        url = reverse('employee-my-avatar')
        response = self.client.post(url, {'avatar': upload_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('avatar_url', response.data)
        self.assertTrue(len(response.data['avatar_url']) > 0)

        self.employee_user.refresh_from_db()
        self.assertTrue(len(self.employee_user.avatar_url) > 0)

    def test_avatar_upload_invalid_type_rejected(self):
        self.client.force_authenticate(user=self.employee_user)
        bad_file = SimpleUploadedFile('document.txt', b'Hello plain text', content_type='text/plain')
        url = reverse('employee-my-avatar')
        response = self.client.post(url, {'avatar': bad_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_avatar_remove(self):
        self.employee_user.avatar_url = '/api/v1/media/1/view/'
        self.employee_user.save()

        self.client.force_authenticate(user=self.employee_user)
        url = reverse('employee-my-avatar')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.employee_user.refresh_from_db()
        self.assertEqual(self.employee_user.avatar_url, '')


class RegistrationAndFlexibleLoginTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.existing_user = Employee.objects.create_user(
            employee_id="BT-1001",
            username="existinguser",
            email="existing@balajitransports.internal",
            phone_number="+919876543210",
            first_name="Existing",
            last_name="User",
            password="ExistingPassword123!",
            role=Employee.Role.EMPLOYEE
        )

    def test_direct_registration_without_otp_success(self):
        url = reverse('auth-register')
        payload = {
            'full_name': 'Manoj Sharma',
            'username': 'manoj.sharma',
            'email': 'manoj@balajitransports.internal',
            'phone_number': '+91 91234 56789',
            'date_of_birth': '1992-05-14',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('employee', response.data)

        # Verify employee in database
        new_emp = Employee.objects.get(username='manoj.sharma')
        self.assertTrue(new_emp.employee_id.startswith('BT-'))
        self.assertEqual(new_emp.email, 'manoj@balajitransports.internal')
        self.assertEqual(new_emp.phone_number, '+919123456789')
        self.assertEqual(new_emp.display_name, 'Manoj Sharma')
        self.assertEqual(new_emp.first_name, 'Manoj')
        self.assertEqual(new_emp.last_name, 'Sharma')
        self.assertTrue(new_emp.check_password('SecurePassword123!'))
        self.assertTrue(new_emp.is_active)

    def test_registration_duplicate_username_rejected(self):
        url = reverse('auth-register')
        payload = {
            'full_name': 'Another User',
            'username': 'existinguser',
            'email': 'unique123@balajitransports.internal',
            'phone_number': '+91 99999 11111',
            'date_of_birth': '1995-01-01',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_registration_duplicate_email_rejected(self):
        url = reverse('auth-register')
        payload = {
            'full_name': 'Another User',
            'username': 'anotheruser',
            'email': 'existing@balajitransports.internal',
            'phone_number': '+91 99999 22222',
            'date_of_birth': '1995-01-01',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_registration_duplicate_phone_rejected(self):
        url = reverse('auth-register')
        payload = {
            'full_name': 'Another User',
            'username': 'anotheruser2',
            'email': 'another2@balajitransports.internal',
            'phone_number': '+91 98765 43210',  # matches existing_user
            'date_of_birth': '1995-01-01',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)

    def test_registration_password_mismatch_rejected(self):
        url = reverse('auth-register')
        payload = {
            'full_name': 'Test User',
            'username': 'testuser',
            'email': 'testuser@balajitransports.internal',
            'phone_number': '+91 90000 00001',
            'date_of_birth': '1990-01-01',
            'password': 'SecurePassword123!',
            'confirm_password': 'DifferentPassword123!'
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_email_success(self):
        url = reverse('auth-login')
        response = self.client.post(url, {
            'identifier': 'existing@balajitransports.internal',
            'password': 'ExistingPassword123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['employee']['employee_id'], 'BT-1001')

    def test_login_with_phone_number_success(self):
        url = reverse('auth-login')
        response = self.client.post(url, {
            'identifier': '+919876543210',
            'password': 'ExistingPassword123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['employee']['employee_id'], 'BT-1001')


class ProfileBioTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()

        self.dept = Department.objects.create(name="Logistics", code="LOG")
        self.user1 = Employee.objects.create_user(
            employee_id="BT-3001",
            username="driver1",
            first_name="Rajesh",
            last_name="Kumar",
            password="Password123!",
            department=self.dept,
            role=Employee.Role.EMPLOYEE
        )

        self.user2 = Employee.objects.create_user(
            employee_id="BT-3002",
            username="driver2",
            first_name="Vikram",
            last_name="Singh",
            password="Password123!",
            department=self.dept,
            role=Employee.Role.EMPLOYEE
        )

    def test_user_can_add_and_update_bio(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('auth-me')

        # Add bio
        response = self.client.patch(url, {'bio': 'Fleet Operations Lead with 8 years experience in South Zone logistics.'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['bio'], 'Fleet Operations Lead with 8 years experience in South Zone logistics.')

        self.user1.refresh_from_db()
        self.assertEqual(self.user1.bio, 'Fleet Operations Lead with 8 years experience in South Zone logistics.')

    def test_bio_exceeding_250_chars_rejected(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('auth-me')

        long_bio = "A" * 251
        response = self.client.patch(url, {'bio': long_bio}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('bio', response.data)

    def test_user_cannot_edit_another_users_bio(self):
        # User 1 attempts to modify User 2's profile
        self.client.force_authenticate(user=self.user1)
        url = reverse('employee-detail', kwargs={'pk': self.user2.pk})

        response = self.client.patch(url, {'bio': 'Hacked bio!'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.user2.refresh_from_db()
        self.assertEqual(self.user2.bio, '')

    def test_bio_visible_in_public_employee_profile(self):
        self.user1.bio = "Passionate transport coordinator."
        self.user1.save()

        self.client.force_authenticate(user=self.user2)
        url = reverse('employee-detail', kwargs={'pk': self.user1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('bio'), "Passionate transport coordinator.")
