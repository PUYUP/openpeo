from django.db import transaction, IntegrityError
from django.db.models import Prefetch, Subquery, OuterRef, F, Sum, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from rest_framework import viewsets, status as response_status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from utils.generals import get_model
from apps.commerce.utils.permissions import IsCreatorOrReject
from apps.commerce.api.transaction.serializers import (
    CartSerializer, CartItemSerializer, OrderSerializer,
    OrderDetailSerializer, SellProductSerializer,
    SellItemSerializer
)
from apps.commerce.utils.constants import DONE

Cart = get_model('commerce', 'Cart')
CartItem = get_model('commerce', 'CartItem')
Order = get_model('commerce', 'Order')
Product = get_model('commerce', 'Product')


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
            queryset = CartItem.objects.get(uuid=item_uuid, cart__user_id=request.user.id)
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
        queryset = Order.objects.prefetch_related(Prefetch('cart'), Prefetch('cart__cart_items'),
                                                  Prefetch('cart__cart_items__product'),
                                                  Prefetch('user'), Prefetch('seller')) \
            .select_related('user', 'seller') \
            .filter(user_id=request.user.id) \
            .annotate(total_item=Sum(F('cart__cart_items__quantity')))

        serializer = OrderSerializer(queryset, many=True, context=context)

        summary = queryset.aggregate(
            total=Sum(F('cart__cart_items__product__price') * F('cart__cart_items__quantity'))
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
        summary = queryset.cart.cart_items.aggregate(total=Sum(F('product__price') * F('quantity')))
 
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

        # mark cart as done
        carts = Cart.objects.filter(user_id=request.user.id)
        if carts.exists():
            carts.update(is_done=True)
        return Response({'detail': 'Order created!'}, status=response_status.HTTP_201_CREATED)


class SellApiView(viewsets.ViewSet):
    lookup_field = 'uuid'
    permission_classes = (IsAuthenticated,)

    def list(self, request, format=None):
        context = {'request': request}
        subitems = CartItem.objects.filter(product_id=OuterRef('id')).values('status')[:1]

        queryset = Product.objects \
            .prefetch_related(Prefetch('user'), Prefetch('cart_items')) \
            .select_related('user') \
            .annotate(
                total=Sum('cart_items__quantity'),
                status=Subquery(subitems)
            ) \
            .filter(user_id=request.user.id) \
            .exclude(Q(cart_items__cart__order_carts__status=DONE))

        serializer = SellProductSerializer(queryset, many=True, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)

    def retrieve(self, request, uuid=None, format=None):
        context = {'request': request}

        try:
            queryset = Product.objects.get(uuid=uuid)
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        # orders become from buyer
        order_items = CartItem.objects \
            .prefetch_related(Prefetch('product'), Prefetch('cart')) \
            .select_related('product', 'cart') \
            .filter(product__uuid=uuid, product__user_id=request.user.id)

        serializer = SellProductSerializer(queryset, many=False, context=context)
        order_items_serializer = SellItemSerializer(order_items, many=True, context=context)

        return Response({'product': serializer.data, 'order_items': order_items_serializer.data}, status=response_status.HTTP_200_OK)
