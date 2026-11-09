from django.contrib import admin
from .models import MediaAttachment

@admin.register(MediaAttachment)
class MediaAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_filename', 'uploader', 'file_type', 'storage_provider', 'file_size_bytes', 'is_deleted', 'created_at')
    list_filter = ('file_type', 'storage_provider', 'is_deleted')
    search_fields = ('original_filename', 'uploader__employee_id', 'storage_file_id')
    readonly_fields = ('file_hash', 'created_at')
