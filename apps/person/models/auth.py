import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser


# Extend User
# https://docs.djangoproject.com/en/3.1/topics/auth/customizing/#substituting-a-custom-user-model
class User(AbstractUser):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    class Meta(AbstractUser.Meta):
        app_label = 'person'
