from .base import *
from .transaction import *
from .chat import *
from .notification import *

# PROJECT UTILS
from utils.generals import is_model_registered

__all__ = list()

# 1
if not is_model_registered('commerce', 'Bank'):
    class Bank(AbstractBank):
        class Meta(AbstractBank.Meta):
            db_table = 'commerce_bank'

    __all__.append('Bank')


# 2
if not is_model_registered('commerce', 'PaymentBank'):
    class PaymentBank(AbstractPaymentBank):
        class Meta(AbstractPaymentBank.Meta):
            db_table = 'commerce_payment_bank'

    __all__.append('PaymentBank')


# 3
if not is_model_registered('commerce', 'DeliveryAddress'):
    class DeliveryAddress(AbstractDeliveryAddress):
        class Meta(AbstractDeliveryAddress.Meta):
            db_table = 'commerce_delivery_address'

    __all__.append('DeliveryAddress')


# 4
if not is_model_registered('commerce', 'Product'):
    class Product(AbstractProduct):
        class Meta(AbstractProduct.Meta):
            db_table = 'commerce_product'

    __all__.append('Product')


# 5
if not is_model_registered('commerce', 'ProductAttachment'):
    class ProductAttachment(AbstractProductAttachment):
        class Meta(AbstractProductAttachment.Meta):
            db_table = 'commerce_product_attachment'

    __all__.append('ProductAttachment')


# 6
if not is_model_registered('commerce', 'Cart'):
    class Cart(AbstractCart):
        class Meta(AbstractCart.Meta):
            db_table = 'commerce_cart'

    __all__.append('Cart')


# 7
if not is_model_registered('commerce', 'CartItem'):
    class CartItem(AbstractCartItem):
        class Meta(AbstractCartItem.Meta):
            db_table = 'commerce_cart_item'

    __all__.append('CartItem')


# 8
if not is_model_registered('commerce', 'Chat'):
    class Chat(AbstractChat):
        class Meta(AbstractChat.Meta):
            db_table = 'commerce_chat'

    __all__.append('Chat')


# 9
if not is_model_registered('commerce', 'ChatMessage'):
    class ChatMessage(AbstractChatMessage):
        class Meta(AbstractChatMessage.Meta):
            db_table = 'commerce_chat_message'

    __all__.append('ChatMessage')


# 10
if not is_model_registered('commerce', 'ChatAttachment'):
    class ChatAttachment(AbstractChatAttachment):
        class Meta(AbstractChatAttachment.Meta):
            db_table = 'commerce_chat_attachment'

    __all__.append('ChatAttachment')


# 11
if not is_model_registered('commerce', 'WishList'):
    class WishList(AbstractWishList):
        class Meta(AbstractWishList.Meta):
            db_table = 'commerce_wishlist'

    __all__.append('WishList')


# 12
if not is_model_registered('commerce', 'Order'):
    class Order(AbstractOrder):
        class Meta(AbstractOrder.Meta):
            db_table = 'commerce_order'

    __all__.append('Order')


# 13
if not is_model_registered('commerce', 'OrderItem'):
    class OrderItem(AbstractOrderItem):
        class Meta(AbstractOrderItem.Meta):
            db_table = 'commerce_order_item'

    __all__.append('OrderItem')


# 14
if not is_model_registered('commerce', 'Notification'):
    class Notification(AbstractNotification):
        class Meta(AbstractNotification.Meta):
            db_table = 'commerce_notification'

    __all__.append('Notification')
