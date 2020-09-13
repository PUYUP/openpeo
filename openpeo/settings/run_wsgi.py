from .production import *

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# SENTRY
sentry_sdk.init(
    dsn="https://fc8ad650d89f42a0be005a19b401449a@o400235.ingest.sentry.io/5419903",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)
