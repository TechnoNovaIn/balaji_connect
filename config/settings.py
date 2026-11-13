import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'balaji-connect-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,10.0.2.2,testserver').split(',') if host.strip()]

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'channels',

    # Balaji Connect local apps
    'accounts.apps.AccountsConfig',
    'media_vault.apps.MediaVaultConfig',
    'posts.apps.PostsConfig',
    'notifications.apps.NotificationsConfig',
    'moderation.apps.ModerationConfig',
    'chat.apps.ChatConfig',
    'stories.apps.StoriesConfig',
    'frontend.apps.FrontendConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'frontend' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Channels Channel Layer (Redis in production / Render, InMemory fallback for local)
REDIS_URL = os.getenv('REDIS_URL', '').strip()
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Database Configuration (Supports PostgreSQL and MySQL)
DB_ENGINE_NAME = os.getenv('DB_ENGINE', 'postgresql').lower()
if 'mysql' in DB_ENGINE_NAME:
    try:
        import pymysql
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
    DEFAULT_DB_BACKEND = 'django.db.backends.mysql'
    DEFAULT_DB_PORT = 3306
else:
    DEFAULT_DB_BACKEND = 'django.db.backends.postgresql'
    DEFAULT_DB_PORT = 5432

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    import urllib.parse
    parsed = urllib.parse.urlparse(DATABASE_URL)
    is_mysql = 'mysql' in parsed.scheme.lower() or 'mysql' in DB_ENGINE_NAME
    backend = 'django.db.backends.mysql' if is_mysql else 'django.db.backends.postgresql'
    port = parsed.port or (3306 if is_mysql else 5432)
    db_options = {'charset': 'utf8mb4'} if is_mysql else {}
    DATABASES = {
        'default': {
            'ENGINE': backend,
            'NAME': parsed.path.lstrip('/'),
            'USER': parsed.username or os.getenv('DB_USER', 'root' if is_mysql else 'postgres'),
            'PASSWORD': urllib.parse.unquote(parsed.password or '') if parsed.password else os.getenv('DB_PASSWORD', ''),
            'HOST': parsed.hostname or os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': port,
            'OPTIONS': db_options,
        }
    }
else:
    is_mysql = DEFAULT_DB_BACKEND == 'django.db.backends.mysql'
    db_options = {'charset': 'utf8mb4'} if is_mysql else {}
    DATABASES = {
        'default': {
            'ENGINE': DEFAULT_DB_BACKEND,
            'NAME': os.getenv('DB_NAME', 'balaji_connect'),
            'USER': os.getenv('DB_USER', 'root' if is_mysql else 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': int(os.getenv('DB_PORT', DEFAULT_DB_PORT)),
            'OPTIONS': db_options,
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'accounts.Employee'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'frontend' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media Files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 15,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
        'login': os.getenv('LOGIN_RATE_LIMIT', '10/minute'),
    }
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_CREDENTIALS = True

# Storage Configuration
STORAGE_DRIVER = os.getenv('STORAGE_DRIVER', 'local')
LOCAL_STORAGE_DIR = BASE_DIR / os.getenv('LOCAL_STORAGE_DIR', 'media_vault_storage')

GOOGLE_DRIVE_CLIENT_ID = os.getenv('GOOGLE_DRIVE_CLIENT_ID', '')
GOOGLE_DRIVE_CLIENT_SECRET = os.getenv('GOOGLE_DRIVE_CLIENT_SECRET', '')
GOOGLE_DRIVE_REFRESH_TOKEN = os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN', '')
GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')

# Security & Session Settings (Persistent Login)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400 * 30  # 30 days persistent session
SESSION_SAVE_EVERY_REQUEST = True  # Rolling session: resets expiration counter on user activity
SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_HTTPONLY = False  # Allows frontend JS to read CSRF token for AJAX POSTs
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG

# Cloudflare Tunnel & Reverse Proxy Trust
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1:8001,http://localhost:8001,http://127.0.0.1:8000,http://localhost:8000').split(',')
    if origin.strip()
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Max upload sizes for smartphone photos & videos (50 MB limit)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB
