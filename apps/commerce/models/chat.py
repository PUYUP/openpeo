import uuid

from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _


class AbstractChat(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True, null=True)
    update_date = models.DateTimeField(auto_now=True, null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='chats')
    send_to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='chats_send_to_user')

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-create_date']
        verbose_name = _(u"Chat")
        verbose_name_plural = _(u"Chats")

    def __str__(self):
        return self.user.username


class AbstractChatMessage(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True, null=True)
    update_date = models.DateTimeField(auto_now=True, null=True)

    chat = models.ForeignKey('commerce.Chat', on_delete=models.CASCADE,
                             related_name='chat_messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='chat_messages')

    # this case Cart make as Room
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,
                                     limit_choices_to={'app_label': 'commerce'},
                                     related_name='chats_content_type',
                                     null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    message = models.TextField()

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-create_date']
        verbose_name = _(u"Chat Message")
        verbose_name_plural = _(u"Chat Messages")

    def __str__(self):
        return self.user.username


class AbstractChatAttachment(models.Model):
    _UPLOAD_TO = 'files/chat'

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True, null=True)
    update_date = models.DateTimeField(auto_now=True, null=True)

    chat = models.ForeignKey('commerce.Chat', on_delete=models.CASCADE,
                             related_name='chat_attachments')

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    attach_type = models.CharField(max_length=255, editable=False)
    attach_file = models.FileField(upload_to=_UPLOAD_TO, max_length=500)

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-create_date']
        verbose_name = _(u"Chat Attachment")
        verbose_name_plural = _(u"Chat Attachments")

    def __str__(self):
        return self.title
