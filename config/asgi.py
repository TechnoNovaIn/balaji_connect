import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django_asgi_app = get_asgi_application()

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing

# Wrap with ASGIStaticFilesHandler so Daphne serves static assets (/static/...) seamlessly
http_handler = ASGIStaticFilesHandler(django_asgi_app) if settings.DEBUG else django_asgi_app

application = ProtocolTypeRouter({
    "http": http_handler,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})
