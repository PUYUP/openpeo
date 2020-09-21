from django.apps import AppConfig
from django.db.models.signals import post_save, post_delete


class CommerceConfig(AppConfig):
    name = 'apps.commerce'

    def ready(self):
        from utils.generals import get_model
        from apps.commerce.signals import (
            order_save_handler, cart_item_delete_handler,
            order_item_save_handler, order_item_delete_handler
        )

        Order = get_model('commerce', 'Order')
        OrderItem = get_model('commerce', 'OrderItem')
        CartItem = get_model('commerce', 'CartItem')

        post_save.connect(order_save_handler, sender=Order, dispatch_uid='order_save_signal')
        post_save.connect(order_item_save_handler, sender=OrderItem, dispatch_uid='order_item_save_signal')
        post_delete.connect(cart_item_delete_handler, sender=CartItem, dispatch_uid='cart_item_delete_handler_signal')
        post_delete.connect(order_item_delete_handler, sender=OrderItem, dispatch_uid='order_item_delete_handler_signal')
