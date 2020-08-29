from django.db import transaction

from utils.generals import get_model

Cart = get_model('commerce', 'Cart')
CartItem = get_model('commerce', 'CartItem')


@transaction.atomic
def order_save_handler(sender, instance, created, **kwargs):
    if created:
        # mark cart done!
        carts = Cart.objects.filter(user_id=instance.user.id)
        if carts.exists():
            carts.update(is_done=True)


@transaction.atomic
def cart_item_delete_handler(sender, instance, **kwargs):
    # delete cart if has not cart item
    cart_items = CartItem.objects.filter(cart_id=instance.cart.id)
    if not cart_items.exists():
        instance.cart.delete()
