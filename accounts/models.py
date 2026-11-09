import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return f"{self.name} ({self.code})"


class EmployeeManager(BaseUserManager):
    def create_user(self, employee_id, username=None, password=None, **extra_fields):
        if not employee_id:
            raise ValueError(_("The Employee ID must be set"))
        if not username:
            username = employee_id.lower()
        
        extra_fields.setdefault('is_active', True)
        user = self.model(employee_id=employee_id, username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, employee_id, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Employee.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(employee_id, username, password, **extra_fields)


class Employee(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrator')
        EMPLOYEE = 'EMPLOYEE', _('Employee')

    employee_id = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text=_("Unique Company Employee ID (e.g. BT-1001)")
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    designation = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        db_index=True
    )
    display_name = models.CharField(max_length=150, blank=True, default='')
    bio = models.CharField(max_length=250, blank=True, default='', help_text=_("Short bio describing the employee (max 250 characters)"))
    date_of_birth = models.DateField(null=True, blank=True, help_text=_("Optional Date of Birth"))
    avatar_url = models.CharField(max_length=500, blank=True, default='')
    must_change_password = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EmployeeManager()

    USERNAME_FIELD = 'employee_id'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ['employee_id']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        constraints = [
            models.UniqueConstraint(
                fields=['email'],
                condition=~models.Q(email=''),
                name='unique_employee_nonempty_email',
            ),
            models.UniqueConstraint(
                fields=['phone_number'],
                condition=~models.Q(phone_number=''),
                name='unique_employee_nonempty_phone',
            ),
        ]

    @property
    def is_administrator(self):
        return self.role == self.Role.ADMIN or self.is_superuser or self.is_staff

    @property
    def full_name(self):
        if self.display_name and self.display_name.strip():
            return self.display_name.strip()
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.employee_id

    def __str__(self):
        return f"{self.employee_id} - {self.full_name} ({self.get_role_display()})"
