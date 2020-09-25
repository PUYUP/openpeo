import json
import requests

from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Prefetch, Subquery, OuterRef, F, Sum, Q
from django.db.models.functions import Coalesce
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.contenttypes.models import ContentType

from rest_framework import viewsets, status as response_status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.pagination import LimitOffsetPagination

from utils.generals import get_model
from apps.commerce.utils.permissions import IsCreatorOrReject
from apps.commerce.api.transaction.serializers import (
    CartSerializer, CartItemSerializer, OrderSerializer,
    OrderDetailSerializer, SellProductSerializer,
    SellItemSerializer, OrderItemSerializer
)
from apps.commerce.utils.constants import DONE, PENDING, NEW

Cart = get_model('commerce', 'Cart')
CartItem = get_model('commerce', 'CartItem')
Order = get_model('commerce', 'Order')
OrderItem = get_model('commerce', 'OrderItem')
Product = get_model('commerce', 'Product')
Notification = get_model('commerce', 'Notification')
Chat = get_model('commerce', 'Chat')
ChatMessage = get_model('commerce', 'ChatMessage')

# Define to avoid used ...().paginate__
_PAGINATOR = LimitOffsetPagination()


# Return a response
def paginate_response(serializer):
    response = dict()
    response['count'] = _PAGINATOR.count
    response['per_page'] = settings.PAGINATION_PER_PAGE
    response['navigate'] = {
        'offset': _PAGINATOR.offset,
        'limit': _PAGINATOR.limit,
        'previous': _PAGINATOR.get_previous_link(),
        'next': _PAGINATOR.get_next_link(),
    }
    response['results'] = serializer.data
    return Response(response, status=response_status.HTTP_200_OK)


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


def send_push_notifcation(token):
    serverToken = 'AAAAUASTcW0:APA91bHQXIbndckM3Pn8wC2xgAf-nPlSRQH8WCCC9VNkzUKxgdgiJ-vZ1lSL75X5HvsGEL5lCkRGfS6yQ8A3mrKd5RiLfAwC1HFpBIotUzDXSdweUHvA8Gwkqrt7CaJGf8wVBqqbSLxS'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'key=' + serverToken,
    }

    body = {
        'notification': {
            'title': 'Notifikasi Open Pe O',
            'body': 'Ada orderan baru!',
            'click_action': 'https://openpeo.com/tabs/tab2'
        },
        'to': token,
        'priority': 'high',
    }

    response = requests.post("https://fcm.googleapis.com/fcm/send",headers = headers, data=json.dumps(body))
    return response.status_code, response.json()


class CartApiView(viewsets.ViewSet):
    lookup_field = 'uuid'
    permission_classes = (IsAuthenticated,)
    permission_action = {
        'list': [IsAuthenticated],
        'create': [IsAuthenticated],
        'destroy': [IsAuthenticated, IsCreatorOrReject],
    }

    def get_permissions(self):
        """
        Instantiates and returns
        the list of permissions that this view requires.
        """
        try:
            # return permission_classes depending on `action`
            return [permission() for permission in self.permission_action
                    [self.action]]
        except KeyError:
            # action is not set return default permission_classes
            return [permission() for permission in self.permission_classes]

    def list(self, request, format=None):
        context = {'request': request}
        queryset = Cart.objects.filter(user_id=request.user.id, is_done=False)
        serializer = CartSerializer(queryset, many=True, context=context)

        summary = queryset.aggregate(
            total=Sum(F('cart_items__product__price') * F('cart_items__quantity'))
        )
    
        return Response({'summary': summary, 'carts': serializer.data}, status=response_status.HTTP_200_OK)

    @method_decorator(never_cache)
    @transaction.atomic
    def create(self, request, format=None):
        context = {'request': request}
        serializer = CartSerializer(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            try:
                serializer.save()
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, uuid=None, format=None):
        context = {'request': request}
        try:
            queryset = Cart.objects.get(uuid=uuid, user_id=request.user.id)
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        serializer = CartSerializer(queryset, many=False, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)

    @method_decorator(never_cache)
    @transaction.atomic
    def destroy(self, request, uuid=None, format=None):
        context = {'request': request}

        # single object
        try:
            queryset = Cart.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        # execute delete
        queryset.delete()
        return Response({'detail': _("Delete success!")}, status=response_status.HTTP_204_NO_CONTENT)

    # UPDATE, DELETE cart items
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['patch', 'delete'], detail=True,
            permission_classes=[IsAuthenticated],
            url_path='items/(?P<item_uuid>[^/.]+)', 
            url_name='view_item_update')
    def view_item_update(self, request, uuid=None, item_uuid=None):
        context = {'request': request}
        method = request.method

        try:
            queryset = CartItem.objects.select_for_update().get(uuid=item_uuid, cart__user_id=request.user.id)
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        if method == 'PATCH':
            serializer = CartItemSerializer(queryset, data=request.data, partial=True, context=context)
            if serializer.is_valid(raise_exception=True):
                try:
                    serializer.save()
                except ValidationError as e:
                    return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
                return Response(serializer.data, status=response_status.HTTP_200_OK)
            return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

        elif method == 'DELETE':
            # execute delete
            queryset.delete()
            return Response(
                {'detail': _("Delete success!")},
                status=response_status.HTTP_204_NO_CONTENT)


class OrderApiView(viewsets.ViewSet):
    lookup_field = 'uuid'
    permission_classes = (IsAuthenticated,)
    permission_action = {
        'list': [IsAuthenticated],
        'create': [IsAuthenticated],
        'destroy': [IsAuthenticated, IsCreatorOrReject],
    }

    def get_permissions(self):
        """
        Instantiates and returns
        the list of permissions that this view requires.
        """
        try:
            # return permission_classes depending on `action`
            return [permission() for permission in self.permission_action
                    [self.action]]
        except KeyError:
            # action is not set return default permission_classes
            return [permission() for permission in self.permission_classes]

    def list(self, request, format=None):
        context = {'request': request}
        queryset = Order.objects.prefetch_related(Prefetch('cart'), Prefetch('order_items__product'),
                                                  Prefetch('user'), Prefetch('seller')) \
            .select_related('user', 'seller') \
            .filter(user_id=request.user.id) \
            .annotate(total_item=Sum(F('order_items__quantity')))

        serializer = OrderSerializer(queryset, many=True, context=context)

        summary = queryset.aggregate(
            total=Sum(F('order_items__product__price') * F('order_items__quantity'))
        )
    
        return Response({'summary': summary, 'orders': serializer.data}, status=response_status.HTTP_200_OK)

    @method_decorator(never_cache)
    @transaction.atomic
    def create(self, request, format=None):
        context = {'request': request}
        serializer = OrderSerializer(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            try:
                serializer.save()
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, uuid=None, format=None):
        context = {'request': request}
        try:
            queryset = Order.objects.get(uuid=uuid, user_id=request.user.id)
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        # get total price
        summary = queryset.order_items.aggregate(
            subtotal=Sum(F('product__price') * F('quantity')),
            shipping=Sum(Coalesce(F('shipping_cost'), 0)),
            total=Sum(F('product__price') * F('quantity') + Coalesce(F('shipping_cost'), 0))
        )
 
        serializer = OrderDetailSerializer(queryset, many=False, context=context)
        return Response({'order': serializer.data, 'summary': summary}, status=response_status.HTTP_200_OK)

    @method_decorator(never_cache)
    @transaction.atomic
    def destroy(self, request, uuid=None, format=None):
        context = {'request': request}

        # single object
        try:
            queryset = Order.objects.get(uuid=uuid)
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        # execute delete
        queryset.delete()
        return Response({'detail': _("Delete success!")}, status=response_status.HTTP_204_NO_CONTENT)

    # LIST, CREATE
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['post'], detail=False,
            permission_classes=[IsAuthenticated],
            url_path='bulks', url_name='view_bulks')
    def view_bulks(self, request, uuid=None):
        """
        Params:
            {
                "sellers": [1, 2, 3],
                "carts": [1, 2, 3]
            }
        """
        context = {'request': request}
        user = request.user

        sellers = request.data.get('sellers')
        sellers_fcm_token = request.data.get('sellers_fcm_token')
        carts = request.data.get('carts')

        if not sellers or not carts:
            return Response({'detail': _("Params missing")}, status=response_status.HTTP_400_BAD_REQUEST)

        # combine seller and cart
        combined = list()
        for i, v in enumerate(sellers):
            d = {'seller': v, 'cart': carts[i]}
            combined.append(d)

        # then prepare insert to database
        bulk_orders = list()
        for c in combined:
            o = Order(seller_id=c['seller'], cart_id=c['cart'], user=request.user)
            bulk_orders.append(o)

        # check cart not in order
        carts_in_order = Order.objects.filter(cart_id__in=carts, user_id=request.user.id)
        if carts_in_order.exists():
            return Response({'detail': 'Cart has in order'}, status=response_status.HTTP_400_BAD_REQUEST)

        # insert at once query avoid transaction race
        try:
            Order.objects.bulk_create(bulk_orders, ignore_conflicts=False)
        except IntegrityError as e:
            return Response({'detail': 'Fatal error!'}, status=response_status.HTTP_400_BAD_REQUEST)

        # get latest orders with PENDING status
        orders = Order.objects.filter(user=user.id, status=PENDING)
        order_items = list()
        notifications = list()
        chat_messages = list()

        for item in orders:
            # extract cart items accros order
            cart_items = item.cart.cart_items.filter(cart__is_done=False)
            for c in cart_items:
                co = OrderItem(order=item, product=c.product, quantity=c.quantity, note=c.note)
                order_items.append(co)

        # create order items once!
        if order_items:
            try:
                with transaction.atomic():
                    OrderItem.objects.bulk_create(order_items, ignore_conflicts=False)
            except IntegrityError as e:
                print(e)

        # get order items accros all order
        order_items_created = OrderItem.objects.filter(order__in=orders.values_list('id', flat=True))
        for item in order_items_created:
            # prepare notifications object
            content_type = ContentType.objects.get_for_model(item)
            notif = Notification(actor=item.order.user, recipient=item.order.seller, verb=NEW,
                                action_object_content_type=content_type,
                                action_object_object_id=item.id)
            notifications.append(notif)

            # collect order item then create a chat
            chat_obj = create_chat(item)
            chat_msg = ChatMessage(chat=chat_obj, user=user, content_type=content_type, object_id=item.id,
                                   message=_("Hay saya memesan ini. Apakah masih ada?"))
            chat_messages.append(chat_msg)

        # create notifications once!
        if notifications:
            try:
                with transaction.atomic():
                    Notification.objects.bulk_create(notifications, ignore_conflicts=False)
            except IntegrityError as e:
                pass

        # create chat messages
        if chat_messages:
            try:
                with transaction.atomic():
                    ChatMessage.objects.bulk_create(chat_messages, ignore_conflicts=False)
            except IntegrityError as e:
                pass

        # send push notifications
        for i, v in enumerate(sellers_fcm_token):
            if v:
                send_push_notifcation(v)

        # mark cart as done
        carts = Cart.objects.filter(user_id=request.user.id)
        if carts.exists():
            carts.update(is_done=True)
        return Response({'detail': 'Order created!'}, status=response_status.HTTP_201_CREATED)

    # UPDATE, DELETE order items
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['patch', 'delete'], detail=True,
            permission_classes=[IsAuthenticated],
            url_path='items/(?P<item_uuid>[^/.]+)', 
            url_name='view_item_update')
    def view_item_update(self, request, uuid=None, item_uuid=None):
        context = {'request': request}
        method = request.method

        try:
            queryset = OrderItem.objects.select_for_update() \
                .get(Q(uuid=item_uuid), Q(order__seller_id=request.user.id) | Q(order__user_id=request.user.id))
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        if method == 'PATCH':
            serializer = OrderItemSerializer(queryset, data=request.data, partial=True, context=context)
            if serializer.is_valid(raise_exception=True):
                try:
                    serializer.save()
                except ValidationError as e:
                    return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
                return Response(serializer.data, status=response_status.HTTP_200_OK)
            return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

        elif method == 'DELETE':
            # execute delete
            queryset.delete()
            return Response(
                {'detail': _("Delete success!")},
                status=response_status.HTTP_204_NO_CONTENT)


class SellApiView(viewsets.ViewSet):
    lookup_field = 'uuid'
    permission_classes = (IsAuthenticated,)

    def list(self, request, format=None):
        context = {'request': request}
        subitems = OrderItem.objects.filter(product_id=OuterRef('id')).values('status')[:1]

        queryset = Product.objects \
            .prefetch_related(Prefetch('user'), Prefetch('order_items')) \
            .select_related('user') \
            .annotate(
                total=Sum('order_items__quantity'),
                status=Subquery(subitems)
            ) \
            .filter(user_id=request.user.id, order_items__isnull=False) \
            .exclude(Q(order_items__order__status=DONE))

        queryset_paginator = _PAGINATOR.paginate_queryset(queryset, request)
        serializer = SellProductSerializer(queryset_paginator, many=True, context=context)
        return paginate_response(serializer)

    def retrieve(self, request, uuid=None, format=None):
        context = {'request': request}

        try:
            queryset = Product.objects.get(uuid=uuid)
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        # orders become from buyer
        order_items = OrderItem.objects \
            .prefetch_related(Prefetch('product'), Prefetch('order')) \
            .select_related('product', 'order') \
            .filter(product__uuid=uuid, product__user_id=request.user.id)

        serializer = SellProductSerializer(queryset, many=False, context=context)
        order_items_serializer = SellItemSerializer(order_items, many=True, context=context)

        return Response({'product': serializer.data, 'order_items': order_items_serializer.data}, status=response_status.HTTP_200_OK)
