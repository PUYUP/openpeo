from datetime import timedelta
from django.contrib.messages import constants as messages

from .base import *


# GLOBAL CONFIGURATIONS
PROJECT_NAME = 'Open Peo'
PROJECT_WEBSITE = 'www.openpeo.com'
PAGINATION_PER_PAGE = 20
CRISPY_TEMPLATE_PACK = 'bootstrap4'
LOGIN_WITH_JWT = True
OTP_COOKIES_EXPIRED = 3000

# REGISTRATION REQUIREMENTS
STRICT_EMAIL = False
STRICT_EMAIL_VERIFIED = False
STRICT_EMAIL_DUPLICATE = True

STRICT_MSISDN = True
STRICT_MSISDN_VERIFIED = False
STRICT_MSISDN_DUPLICATE = True

LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/person/login/'


# Application definition
PROJECT_APPS = [
    'channels',
    'corsheaders',
    'rest_framework',
    'crispy_forms',
    'django_celery_results',
    'apps.person.apps.PersonConfig',
    'apps.commerce.apps.CommerceConfig',
]
INSTALLED_APPS = INSTALLED_APPS + PROJECT_APPS


# Extend User
# https://docs.djangoproject.com/en/3.1/topics/auth/customizing/#auth-custom-user
AUTH_USER_MODEL = 'person.User'


# MIDDLEWARES
PROJECT_MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django_currentuser.middleware.ThreadLocalUserMiddleware',
]
MIDDLEWARE = MIDDLEWARE + PROJECT_MIDDLEWARE


# Specifying authentication backends
# https://docs.djangoproject.com/en/3.0/topics/auth/customizing/
AUTHENTICATION_BACKENDS = ['apps.person.utils.auth.LoginBackend',]


# CACHING
# https://docs.djangoproject.com/en/2.2/topics/cache/
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "OPTIONS": {
            "SELLER_CLASS": "django_redis.seller.DefaultClient"
        },
        "KEY_PREFIX": "openpeo_cache"
    }
}


# MESSAGES
# https://docs.djangoproject.com/en/3.0/ref/contrib/messages/
MESSAGE_TAGS = {
    messages.DEBUG: 'alert alert-dark shadow-sm',
    messages.INFO: 'alert alert-info shadow-sm',
    messages.SUCCESS: 'alert alert-info success shadow-sm',
    messages.WARNING: 'alert alert-warning shadow-sm',
    messages.ERROR: 'alert alert-error shadow-sm',
}


# Django Sessions
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/2.2/ref/settings/
SESSION_SAVE_EVERY_REQUEST = False
SESSION_ENGINE = 'django.contrib.sessions.backends.db'


# Static files (CSS, JavaScript, Images)
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/2.2/howto/static-files/
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(PROJECT_PATH, '{0}/media/'.format(PUBLIC_DIR_NAME))


# Django Simple JWT
# ------------------------------------------------------------------------------
# https://github.com/davesque/django-rest-framework-simplejwt
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=365),
}


# Django Rest Framework (DRF)
# ------------------------------------------------------------------------------
# https://www.django-rest-framework.org/
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication'
    ],
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.'
                                'NamespaceVersioning',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': PAGINATION_PER_PAGE
}


# Email Configuration
# https://docs.djangoproject.com/en/3.0/topics/email/
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


# Channels
ASGI_APPLICATION = 'openpeo.routing.application'
