from django.contrib import admin
from .models import ContentReport, AuditLog

@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'reason', 'status', 'reviewed_by', 'reviewed_at', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('reporter__employee_id', 'description', 'admin_notes')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'actor', 'action', 'target_model', 'target_id', 'created_at')
    list_filter = ('action', 'target_model', 'created_at')
    search_fields = ('actor__employee_id', 'action', 'target_id')
