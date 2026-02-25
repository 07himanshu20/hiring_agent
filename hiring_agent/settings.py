import os
import environ
from pathlib import Path
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Initialize environment variables
env = environ.Env()
environ.Env.read_env()

# Gemini AI Configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-development-key')

DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Add this to your settings.py to debug
import os
print("=== ENVIRONMENT VARIABLES ===")
print(f"GEMINI_API_KEY exists: {'GEMINI_API_KEY' in os.environ}")
if 'GEMINI_API_KEY' in os.environ:
    print(f"GEMINI_API_KEY length: {len(os.environ['GEMINI_API_KEY'])}")
    print(f"GEMINI_API_KEY starts with: {os.environ['GEMINI_API_KEY'][:10]}...")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'hiring',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'hiring.middleware.RateLimitMiddleware',
]

ROOT_URLCONF = 'hiring_agent.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'hiring_agent.wsgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
    }
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

api_key = os.getenv('GEMINI_API_KEY')
print(f"GEMINI_API_KEY from os.getenv: {api_key is not None}")
if api_key:
    print(f"GEMINI_API_KEY length: {len(api_key)}")
    print(f"GEMINI_API_KEY preview: {api_key[:10]}...")
else:
    print("❌ GEMINI_API_KEY is None or empty")

# Custom settings
GEMINI_API_KEY = env('GEMINI_API_KEY', default=None)
ELEVENLABS_API_KEY = env('ELEVENLABS_API_KEY', default=None)
OPENAI_API_KEY = env('OPENAI_API_KEY', default=None)
STT_MODE = env('STT_MODE', default='local')
MOCK_MODE = env.bool('MOCK_MODE', default=False)
ELEVENLABS_VOICE_ID = env('ELEVENLABS_VOICE_ID', default='21m00Tcm4TlvDq8ikWAM')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Add this at the bottom of settings.py
LOGIN_REDIRECT_URL = '/recruiter/dashboard/'
LOGIN_URL = '/recruiter/login/'
LOGOUT_REDIRECT_URL = '/recruiter/login/'