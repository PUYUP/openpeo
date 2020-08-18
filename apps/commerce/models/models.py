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
