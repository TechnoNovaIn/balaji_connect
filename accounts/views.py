import logging
from django.conf import settings
from django.contrib.auth import login, logout

logger = logging.getLogger(__name__)
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action

from media_vault.models import MediaAttachment
from media_vault.validators import calculate_sha256
from media_vault.services import get_storage_service

from .models import Employee, Department
from .serializers import (
    DepartmentSerializer,
    EmployeePublicSerializer,
    EmployeeDetailSerializer,
    EmployeeCreateSerializer,
    LoginSerializer,
    RegisterSerializer,
    ChangePasswordSerializer,
    AdminResetPasswordSerializer,
    AvatarUploadSerializer,
)
from .permissions import IsActiveEmployee, IsAdminRole, IsSelfOrAdmin
from .throttling import LoginRateThrottle


class RegisterView(views.APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Log into browser session
        login(request, user)
        request.session.set_expiry(86400 * 30)

        token, _ = Token.objects.get_or_create(user=user)
        employee_data = EmployeeDetailSerializer(user, context={'request': request}).data

        return Response({
            'detail': 'Registration successful.',
            'token': token.key,
            'employee': employee_data
        }, status=status.HTTP_201_CREATED)


class LoginView(views.APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        remember_me = bool(request.data.get('remember_me', True))

        # Browser session login
        login(request, user)
        if remember_me:
            # 30-day persistent rolling session
            request.session.set_expiry(86400 * 30)
        else:
            # Session ends when browser closes
            request.session.set_expiry(0)

        # Token for Android / API clients
        token, _ = Token.objects.get_or_create(user=user)

        employee_data = EmployeeDetailSerializer(user, context={'request': request}).data

        return Response({
            'detail': 'Login successful.',
            'token': token.key,
            'employee': employee_data
        }, status=status.HTTP_200_OK)


class LogoutView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Invalidate auth token if user is authenticated
        if request.user and request.user.is_authenticated:
            try:
                Token.objects.filter(user=request.user).delete()
            except Exception:
                pass

        # Clear session and flush cookies
        logout(request)

        response = Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        # Explicitly instruct the browser to delete sessionid and csrf cookies
        response.delete_cookie(settings.SESSION_COOKIE_NAME, path=getattr(settings, 'SESSION_COOKIE_PATH', '/'))
        return response


class MeView(views.APIView):
    permission_classes = [IsActiveEmployee]

    def get(self, request):
        serializer = EmployeeDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = EmployeeDetailSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(views.APIView):
    permission_classes = [IsActiveEmployee]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': ['Current password is incorrect.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(serializer.validated_data['new_password'])
        user.must_change_password = False
        user.save()

        # Update session auth hash so user is not logged out in browser
        login(request, user)

        return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminRole()]
        return [IsActiveEmployee()]


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related('department').all()

    def get_permissions(self):
        if self.action == 'create':
            return [IsAdminRole()]
        if self.action in ['update', 'partial_update']:
            return [IsSelfOrAdmin()]
        if self.action in ['destroy', 'toggle_status', 'reset_password']:
            return [IsAdminRole()]
        return [IsActiveEmployee()]

    def get_serializer_class(self):
        if self.action == 'create':
            return EmployeeCreateSerializer
        if self.action in ['retrieve', 'update', 'partial_update']:
            return EmployeeDetailSerializer
        # If user is admin viewing list, allow detail serializer; otherwise public
        if self.request.user and self.request.user.is_authenticated and self.request.user.is_administrator:
            return EmployeeDetailSerializer
        return EmployeePublicSerializer

    @property
    def paginator(self):
        if self.request.query_params.get('all') == 'true':
            return None
        return super().paginator

    def get_queryset(self):
        qs = super().get_queryset()
        # Non-admins only see active employees
        if not (self.request.user and self.request.user.is_authenticated and self.request.user.is_administrator):
            qs = qs.filter(is_active=True)

        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(display_name__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(designation__icontains=search) |
                Q(department__name__icontains=search)
            )

        department = self.request.query_params.get('department')
        if department:
            qs = qs.filter(department_id=department)

        return qs

    @action(detail=True, methods=['post'], permission_classes=[IsAdminRole])
    def toggle_status(self, request, pk=None):
        employee = self.get_object()
        if employee == request.user:
            return Response(
                {'detail': 'Administrators cannot deactivate their own account.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        employee.is_active = not employee.is_active
        employee.save(update_fields=['is_active'])

        # If deactivated, invalidate any tokens immediately
        if not employee.is_active:
            Token.objects.filter(user=employee).delete()

        status_text = 'activated' if employee.is_active else 'deactivated'
        return Response({
            'detail': f'Employee account {status_text} successfully.',
            'is_active': employee.is_active
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminRole])
    def reset_password(self, request, pk=None):
        employee = self.get_object()
        serializer = AdminResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee.set_password(serializer.validated_data['new_password'])
        employee.must_change_password = True
        employee.save(update_fields=['password', 'must_change_password'])

        # Invalidate old tokens to force re-login
        Token.objects.filter(user=employee).delete()

        return Response({'detail': f'Password reset successfully for {employee.employee_id}.'})

    @action(detail=False, methods=['get'], permission_classes=[IsActiveEmployee])
    def birthdays(self, request):
        from notifications.services import check_and_dispatch_daily_birthdays
        check_and_dispatch_daily_birthdays()
        today = timezone.localdate()
        birthday_employees = Employee.objects.filter(
            is_active=True,
            date_of_birth__isnull=False,
            date_of_birth__month=today.month,
            date_of_birth__day=today.day
        ).select_related('department')

        results = []
        for emp in birthday_employees:
            results.append({
                'id': emp.id,
                'employee_id': emp.employee_id,
                'full_name': emp.full_name,
                'display_name': emp.display_name,
                'department_name': emp.department.name if emp.department else '',
                'avatar_url': emp.avatar_url,
                'birthday_formatted': today.strftime('%B %d'),
            })
        return Response(results)

    @action(detail=False, methods=['post', 'delete'], permission_classes=[IsActiveEmployee], parser_classes=[MultiPartParser, FormParser], url_path='me/avatar')
    def my_avatar(self, request):
        user = request.user
        if request.method == 'DELETE':
            user.avatar_url = ''
            user.save(update_fields=['avatar_url'])
            return Response({'detail': 'Profile picture removed.', 'avatar_url': ''}, status=status.HTTP_200_OK)

        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_obj = serializer.validated_data['avatar']

        file_hash = calculate_sha256(file_obj)
        storage = get_storage_service()
        try:
            upload_result = storage.upload_file(
                file_obj=file_obj,
                filename=file_obj.name,
                content_type=file_obj.content_type,
                file_size=file_obj.size
            )
        except Exception as e:
            if getattr(storage, 'provider_name', '') != 'local':
                logger.warning(
                    "Primary storage driver '%s' failed for avatar (%s). Falling back to local storage.",
                    getattr(storage, 'provider_name', ''), e
                )
                local_storage = get_storage_service(provider='local')
                upload_result = local_storage.upload_file(
                    file_obj=file_obj,
                    filename=file_obj.name,
                    content_type=file_obj.content_type,
                    file_size=file_obj.size
                )
            else:
                raise
        attachment = MediaAttachment.objects.create(
            uploader=user,
            storage_provider=upload_result['provider'],
            storage_file_id=upload_result['storage_file_id'],
            original_filename=file_obj.name,
            file_type='IMAGE',
            mime_type=file_obj.content_type,
            file_size_bytes=file_obj.size,
            file_hash=file_hash,
        )
        avatar_url = attachment.get_view_url(request=request)
        user.avatar_url = avatar_url
        user.save(update_fields=['avatar_url'])

        return Response({
            'detail': 'Profile picture updated successfully.',
            'avatar_url': avatar_url
        }, status=status.HTTP_200_OK)
