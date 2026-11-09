from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContentReportViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'reports', ContentReportViewSet, basename='report')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]

