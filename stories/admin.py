from django.contrib import admin
from .models import Story, StoryView


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'media_type', 'created_at', 'expires_at', 'is_expired')
    list_filter = ('media_type', 'created_at', 'expires_at')
    search_fields = ('author__full_name', 'author__username', 'caption')


@admin.register(StoryView)
class StoryViewAdmin(admin.ModelAdmin):
    list_display = ('id', 'story', 'viewer', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('viewer__full_name', 'viewer__username')
