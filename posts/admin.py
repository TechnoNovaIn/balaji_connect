from django.contrib import admin
from .models import Post, PostReaction, Comment

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'content_snippet', 'like_count', 'comment_count', 'is_deleted', 'created_at')
    list_filter = ('is_deleted', 'created_at')
    search_fields = ('content', 'author__employee_id', 'author__first_name')

    def content_snippet(self, obj):
        return obj.content[:50]


@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'reaction_type', 'created_at')
    list_filter = ('reaction_type',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'author', 'content_snippet', 'is_deleted', 'created_at')
    list_filter = ('is_deleted', 'created_at')

    def content_snippet(self, obj):
        return obj.content[:50]
