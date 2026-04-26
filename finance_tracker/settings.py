import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# 1. Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Security & Environment
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-fallback-key')

# On Render, set DEBUG to False in Environment Variables
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# 1. Update your Allowed Hosts
ALLOWED_HOSTS = ['tillybudget.onrender.com', 'localhost', '127.0.0.1']

# 2. Update your CSRF Trusted Origins (crucial for logins)
CSRF_TRUSTED_ORIGINS = [
    'https://tillybudget.onrender.com',
]
# 3. Application Definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'finances', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Essential for serving CSS on Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'finance_tracker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'finance_tracker.wsgi.application'

# 4. Database configuration (Retool PostgreSQL / Local SQLite fallback)
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# 5. Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 6. Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# 7. Static Files (Production Configuration)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# This ensures your CSS is compressed and cached properly
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 8. Authentication Redirects
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# 9. Default Auto Field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

import os

# Grab the Gemini API key from the .env file
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')