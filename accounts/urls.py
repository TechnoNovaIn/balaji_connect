from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView,
    RegisterView,
    LogoutView,
    MeView,
    ChangePasswordView,
    DepartmentViewSet,
    EmployeeViewSet,
)

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'employees', EmployeeViewSet, basename='employee')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('', include(router.urls)),
]

