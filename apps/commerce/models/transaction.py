import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.commerce.utils.constants import ORDER_STATUS, PENDING


class AbstractOrder(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    date_updated = models.DateTimeField(auto_now=True, null=True)

    # map Buyer to Seller
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='order_buyers')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='order_sellers')

    shipping_cost = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(choices=ORDER_STATUS, default=PENDING,
                              max_length=15, null=True)

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-date_created']

    def __str__(self):
        return self.buyer.username


class AbstractOrderItem(models.Model):
    """Each order make sure has unique product"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    date_updated = models.DateTimeField(auto_now=True, null=True)

    order = models.ForeignKey('commerce.Order', on_delete=models.CASCADE,
                              related_name='order_items')
    product = models.ForeignKey('commerce.Product', on_delete=models.CASCADE,
                                related_name='order_items')

    quantity = models.IntegerField()
    note = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-date_created']
        constraints = [
            models.UniqueConstraint(fields=['order', 'product'], name='unique_order_product')
        ]

    def __str__(self):
        if self.product:
            return self.product.name
        return ''
