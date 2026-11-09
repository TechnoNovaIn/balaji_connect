import re
from datetime import date
from PIL import Image
from rest_framework import serializers
from django.db.models import Q
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import Employee, Department


def get_next_employee_id():
    eids = Employee.objects.filter(employee_id__startswith='BT-').values_list('employee_id', flat=True)
    highest = 1000
    for eid in eids:
        m = re.match(r'^BT-(\d+)$', str(eid).strip())
        if m:
            val = int(m.group(1))
            if val > highest:
                highest = val
    return f"BT-{highest + 1}"

class DepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(source='employees.count', read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'description', 'employee_count', 'created_at']


class EmployeePublicSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_code = serializers.CharField(source='department.code', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id',
            'employee_id',
            'username',
            'full_name',
            'display_name',
            'first_name',
            'last_name',
            'bio',
            'department',
            'department_name',
            'department_code',
            'designation',
            'avatar_url',
            'role',
            'is_active',
        ]
        read_only_fields = fields


class EmployeeDetailSerializer(serializers.ModelSerializer):
    department_details = DepartmentSerializer(source='department', read_only=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    bio = serializers.CharField(max_length=250, required=False, allow_blank=True)

    def validate_date_of_birth(self, value):
        if value == '' or value is None:
            return None
        return value

    class Meta:
        model = Employee
        fields = [
            'id',
            'employee_id',
            'username',
            'display_name',
            'bio',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'date_of_birth',
            'department',
            'department_details',
            'designation',
            'phone_number',
            'avatar_url',
            'role',
            'is_active',
            'must_change_password',
            'created_at',
            'last_login',
        ]
        read_only_fields = ['id', 'created_at', 'last_login']

    def to_internal_value(self, data):
        # Convert empty string date_of_birth to None
        mutable_data = data.copy() if hasattr(data, 'copy') else dict(data)
        if 'date_of_birth' in mutable_data and mutable_data['date_of_birth'] == '':
            mutable_data['date_of_birth'] = None
        return super().to_internal_value(mutable_data)

    def update(self, instance, validated_data):
        user = self.context['request'].user
        # Non-admins cannot alter their role, employee_id, is_active, is_staff, is_superuser, or administrative assignments
        if not user.is_administrator:
            validated_data.pop('role', None)
            validated_data.pop('employee_id', None)
            validated_data.pop('is_active', None)
            validated_data.pop('department', None)
            validated_data.pop('designation', None)
            validated_data.pop('is_staff', None)
            validated_data.pop('is_superuser', None)
        return super().update(instance, validated_data)


class EmployeeCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = Employee
        fields = [
            'id',
            'employee_id',
            'username',
            'email',
            'first_name',
            'last_name',
            'department',
            'designation',
            'phone_number',
            'avatar_url',
            'role',
            'password',
        ]
        extra_kwargs = {
            'username': {'required': False},
            'email': {'required': False},
        }

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        employee = Employee.objects.create_user(
            password=password,
            **validated_data
        )
        return employee


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True, help_text="Email address, phone number, username, or employee ID")
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        identifier = attrs.get('identifier', '').strip()
        password = attrs.get('password')

        emp = Employee.objects.filter(
            Q(email__iexact=identifier) |
            Q(phone_number__iexact=identifier) |
            Q(username__iexact=identifier) |
            Q(employee_id__iexact=identifier)
        ).first()
        if not emp:
            raise serializers.ValidationError({"detail": "Invalid credentials. Please verify your email, phone, or password."})

        if not emp.is_active:
            raise serializers.ValidationError({"detail": "This employee account has been deactivated. Please contact your company administrator."})

        if not emp.check_password(password):
            raise serializers.ValidationError({"detail": "Invalid credentials. Please verify your email, phone, or password."})

        attrs['user'] = emp
        return attrs


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True, max_length=150)
    username = serializers.CharField(required=True, max_length=150)
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(required=True, max_length=20)
    date_of_birth = serializers.DateField(required=True)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_username(self, value):
        username = value.strip().lower()
        if not username:
            raise serializers.ValidationError("Username cannot be blank.")
        if not re.match(r'^[\w.@+-]+$', username):
            raise serializers.ValidationError("Enter a valid username (letters, digits, and @/./+/-/_).")
        if Employee.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return username

    def validate_email(self, value):
        email = value.strip().lower()
        if not email:
            raise serializers.ValidationError("Email cannot be blank.")
        if Employee.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An employee with this email address is already registered.")
        return email

    def validate_phone_number(self, value):
        raw = value.strip()
        phone = re.sub(r'[^\d+]', '', raw)
        if len(phone) < 7:
            raise serializers.ValidationError("Enter a valid phone number (at least 7 digits).")
        if Employee.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError("An employee with this phone number is already registered.")
        return phone

    def validate_date_of_birth(self, value):
        if value >= date.today():
            raise serializers.ValidationError("Date of birth must be in the past.")
        return value

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        full_name = validated_data.pop('full_name').strip()
        
        parts = full_name.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        employee_id = get_next_employee_id()

        employee = Employee.objects.create_user(
            employee_id=employee_id,
            username=validated_data['username'],
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            date_of_birth=validated_data['date_of_birth'],
            first_name=first_name,
            last_name=last_name,
            display_name=full_name,
            password=password,
            role=Employee.Role.EMPLOYEE,
        )
        return employee



class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class AdminResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.FileField(required=True)

    ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
    MAX_SIZE = 5 * 1024 * 1024  # 5 MB

    def validate_avatar(self, file_obj):
        content_type = getattr(file_obj, 'content_type', '').lower()
        if content_type not in self.ALLOWED_MIME_TYPES:
            raise serializers.ValidationError(
                f"Unsupported image format '{content_type}'. Allowed types: JPEG, PNG, WEBP."
            )

        if file_obj.size > self.MAX_SIZE:
            raise serializers.ValidationError(
                f"Avatar file exceeds the maximum limit of {self.MAX_SIZE // (1024 * 1024)} MB."
            )

        try:
            file_obj.seek(0)
            img = Image.open(file_obj)
            img.verify()
            file_obj.seek(0)
        except Exception:
            raise serializers.ValidationError("Invalid or corrupted image file.")

        return file_obj
