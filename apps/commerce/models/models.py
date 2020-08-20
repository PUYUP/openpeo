from .base import *
from .transaction import *
from .chat import *

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
if not is_model_registered('commerce', 'Order'):
    class Order(AbstractOrder):
        class Meta(AbstractOrder.Meta):
            db_table = 'commerce_order'

    __all__.append('Order')


# 7
if not is_model_registered('commerce', 'OrderItem'):
    class OrderItem(AbstractOrderItem):
        class Meta(AbstractOrderItem.Meta):
            db_table = 'commerce_order_item'

    __all__.append('OrderItem')


# 8
if not is_model_registered('commerce', 'Chat'):
    class Chat(AbstractChat):
        class Meta(AbstractChat.Meta):
            db_table = 'commerce_chat'

    __all__.append('Chat')


# 9
if not is_model_registered('commerce', 'ChatAttachment'):
    class ChatAttachment(AbstractChatAttachment):
        class Meta(AbstractChatAttachment.Meta):
            db_table = 'commerce_chat_attachment'

    __all__.append('ChatAttachment')
