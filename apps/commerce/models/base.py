import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AbstractBank(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True, null=True)
    update_date = models.DateTimeField(auto_now=True, null=True)

    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['name']
        verbose_name = _(u"Bank")
        verbose_name_plural = _(u"Banks")

    def __str__(self):
        return self.name


class AbstractPaymentBank(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True, null=True)
    update_date = models.DateTimeField(auto_now=True, null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='payment_banks')
    bank = models.ForeignKey('commerce.Bank', on_delete=models.CASCADE,
                             related_name='payment_banks')

    name = models.CharField(max_length=255)
    number = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-create_date']
        verbose_name = _(u"Payment Bank")
        verbose_name_plural = _(u"Payment Banks")

    def __str__(self):
        return self.user.username


class AbstractDeliveryAddress(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True, null=True)
    update_date = models.DateTimeField(auto_now=True, null=True)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='address')
    address = models.TextField()

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-create_date']
        verbose_name = _(u"Delivery Address")
        verbose_name_plural = _(u"Delivery Address")

    def __str__(self):
        return self.user.username


class AbstractProduct(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True, null=True)
    update_date = models.DateTimeField(auto_now=True, null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='products')

    name = models.CharField(max_length=255)
    price = models.BigIntegerField()
    description = models.TextField()
    order_deadline = models.DateTimeField()
    delivery_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-create_date']
        verbose_name = _(u"Product")
        verbose_name_plural = _(u"Products")

    def __str__(self):
        return self.name


class AbstractProductAttachment(models.Model):
    _UPLOAD_TO = 'files/product'

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True, null=True)
    update_date = models.DateTimeField(auto_now=True, null=True)

    product = models.ForeignKey('commerce.Product', on_delete=models.CASCADE,
                                related_name='product_attachments')

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    attach_type = models.CharField(max_length=255, editable=False)
    attach_file = models.FileField(upload_to=_UPLOAD_TO, max_length=500)

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-create_date']
        verbose_name = _(u"Product Attachment")
        verbose_name_plural = _(u"Product Attachments")

    def __str__(self):
        return self.title
