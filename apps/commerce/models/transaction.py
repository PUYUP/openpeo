import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.commerce.utils.constants import ORDER_STATUS, PENDING


class AbstractCart(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    date_updated = models.DateTimeField(auto_now=True, null=True)

    # map Buyer to Seller
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='cart_users')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='cart_sellers')
    is_done = models.BooleanField(default=False, null=True, editable=False)

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-date_created']

    def __str__(self):
        return self.user.username


class AbstractCartItem(models.Model):
    """Each cart make sure has unique product"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    date_updated = models.DateTimeField(auto_now=True, null=True)

    cart = models.ForeignKey('commerce.Cart', on_delete=models.CASCADE,
                             related_name='cart_items')
    product = models.ForeignKey('commerce.Product', on_delete=models.CASCADE,
                                related_name='cart_items')

    quantity = models.IntegerField()
    note = models.TextField(null=True, blank=True)
    status = models.CharField(choices=ORDER_STATUS, default=PENDING,
                              max_length=15, null=True)

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-date_created']
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product'], name='unique_cart_product')
        ]

    def __str__(self):
        if self.product:
            return self.product.name
        return ''


class AbstractOrder(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    date_updated = models.DateTimeField(auto_now=True, null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='order_users')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='order_sellers', editable=False)
    cart = models.ForeignKey('commerce.Cart', on_delete=models.CASCADE,
                             related_name='order_carts')

    shipping_cost = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(choices=ORDER_STATUS, default=PENDING,
                              max_length=15, null=True)

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-date_created']

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        seller = self.cart.seller
        if seller:
            self.seller = seller

        super().save(*args, **kwargs)


class AbstractWishList(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    date_updated = models.DateTimeField(auto_now=True, null=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='wishlists')
    product = models.ForeignKey('commerce.Product', on_delete=models.CASCADE,
                                related_name='wishlists')

    class Meta:
        abstract = True
        app_label = 'commerce'
        ordering = ['-date_created']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'], name='unique_user_product')
        ]

    def __str__(self):
        if self.product:
            return self.product.name
        return ''
