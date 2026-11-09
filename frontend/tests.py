from django.test import TestCase
from django.urls import reverse
from accounts.models import Employee, Department

class FrontendViewTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Fleet Management", code="FM")
        self.employee = Employee.objects.create_user(
            employee_id="BT-6001",
            first_name="Ravi",
            last_name="Shankar",
            password="Password123!",
            department=self.dept
        )

    def test_unauthenticated_redirect_to_login(self):
        response = self.client.get(reverse('frontend:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('frontend:login'), response.url)

    def test_login_page_renders(self):
        response = self.client.get(reverse('frontend:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Balaji Connect')
        self.assertContains(response, 'Employee ID')
        self.assertContains(response, 'Remember me on this device')

    def test_authenticated_employee_can_view_feed(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('frontend:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Balaji Connect')
        self.assertContains(response, 'Company Feed')

    def test_deactivated_employee_session_purged_on_access(self):
        self.client.force_login(self.employee)
        
        # Administrator deactivates employee account
        self.employee.is_active = False
        self.employee.save(update_fields=['is_active'])

        response = self.client.get(reverse('frontend:home'))
        self.assertEqual(response.status_code, 302)
        # Deactivated user cannot access protected feed and is redirected to login
        self.assertIn(reverse('frontend:login'), response.url)

    def test_login_page_shows_deactivated_message(self):
        response = self.client.get(reverse('frontend:login') + '?deactivated=true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'deactivated')
