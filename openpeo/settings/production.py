import sys

from .base import *
from .project import *

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'marketion.herokuapp.com']


# SENTRY
sentry_sdk.init(
    dsn="https://08b6a2d0e4f947d7a966a7921ffa76dc@o400235.ingest.sentry.io/5282976",
    integrations=[DjangoIntegration()],

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)


# Django Sessions
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/2.2/ref/settings/
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = None
SESSION_COOKIE_HTTPONLY = True

SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 5
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'


# Django csrf
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/2.2/ref/csrf/
CSRF_COOKIE_SECURE = True
# CSRF_TRUSTED_ORIGINS = [
#     'opsional001.firebaseapp.com'
# ]


# Django CORS
# ------------------------------------------------------------------------------
# https://pypi.org/project/django-cors-headers/
CORS_ALLOW_CREDENTIALS = True
# CORS_ORIGIN_WHITELIST = [
#     'https://opsional001.firebaseapp.com'
# ]


# Static files (CSS, JavaScript, Images)
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/2.2/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PROJECT_PATH, '{0}/static/'.format(PUBLIC_DIR_NAME))


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'd4qs9i1jc7m49',
        'USER': 'qveldyqqkiawhe',
        'PASSWORD': 'da8daaf52fcdff7ccc813c3b593881fd4bc9220238a78cba244135604c6586f7',
        'HOST': 'ec2-50-17-90-177.compute-1.amazonaws.com',
        'PORT': '5432'
    }
}


# REDIS
REDIS_URL = os.environ.get('REDIS_URL', '')


# SENDGRID
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = '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'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
