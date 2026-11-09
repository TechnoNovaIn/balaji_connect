from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('accounts.urls')),
    path('api/v1/media/', include('media_vault.urls')),
    path('api/v1/', include('posts.urls')),
    path('api/v1/', include('notifications.urls')),
    path('api/v1/chat/', include('chat.urls')),
    path('api/v1/', include('stories.urls')),
    path('api/v1/', include('moderation.urls')),
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    path('static/<path:path>', serve, {'document_root': settings.BASE_DIR / 'frontend' / 'static'}),
    path('', include('frontend.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
