from django.db import transaction
from django.db.models import Prefetch, Q
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from utils.generals import get_model
from apps.commerce.utils.constants import (
    PENDING, CONFIRMED, NEW, ACCEPTED, PAYMENT_CONFIRMATION, PAYED, DELIVER,
    REJECTED, CANCELED, PAYMENT_CONFIRMED, DONE
)

Cart = get_model('commerce', 'Cart')
CartItem = get_model('commerce', 'CartItem')
Notification = get_model('commerce', 'Notification')
Chat = get_model('commerce', 'Chat')
ChatMessage = get_model('commerce', 'ChatMessage')


def create_chat(order_item):
    # if user has chat or send chat by other user, just get the chat. Not created again.
    user = order_item.order.seller
    send_to_user = order_item.order.user

    try:
        obj = Chat.objects \
            .prefetch_related(Prefetch('user'), Prefetch('send_to_user')) \
            .select_related('user', 'send_to_user') \
            .filter((Q(user_id=user.id) & Q(send_to_user__id=send_to_user.id))
                    | (Q(user_id=send_to_user.id) & Q(send_to_user__id=user.id))
        ).get()
    except ObjectDoesNotExist:
        obj = Chat.objects.create(user=user, send_to_user=send_to_user)

    return obj


def create_chat_message(chat, order_item):
    user = order_item.order.seller
    send_to_user = order_item.order.user

    # create message
    content_type = ContentType.objects.get_for_model(order_item)
    ChatMessage.objects.create(chat=chat, user=user, content_type=content_type, object_id=order_item.id,
                               message=_("Pesanan diterima. Silahkan selesaikan pembayaran "
                                         "melalui rekening dibawah ini."))

@transaction.atomic
def order_save_handler(sender, instance, created, **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    verb = NEW

    if created:
        # mark cart done!
        carts = Cart.objects.filter(user_id=instance.user.id)
        if carts.exists():
            carts.update(is_done=True)


@transaction.atomic
def order_item_save_handler(sender, instance, created, **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    verb = NEW

    if not created:
        # action by seller
        if instance.status == PAYED:
            verb = PAYMENT_CONFIRMED
    
        # action by seller
        if instance.status == CONFIRMED:
            verb = ACCEPTED

            # create chat message
            chat_obj = create_chat(instance)
            if chat_obj:
                create_chat_message(chat_obj, instance)

        # action by seller
        if instance.status == DELIVER:
            verb = DELIVER

        # action by seller
        if instance.status == REJECTED:
            verb = REJECTED

        # action by seller
        if instance.status == DONE:
            verb = DONE

        # action by buyer
        if instance.status == CANCELED:
            verb = CANCELED

    # send notification
    Notification.objects.create(actor=instance.order.seller, recipient=instance.order.user,
                                action_object_content_type=content_type,
                                action_object_object_id=instance.id,
                                verb=verb)


@transaction.atomic
def cart_item_delete_handler(sender, instance, **kwargs):
    # delete cart if has not cart item
    try:
        cart_items = CartItem.objects.filter(cart_id=instance.cart.id)
        if not cart_items.exists():
            instance.cart.delete()
    except ObjectDoesNotExist:
        pass
