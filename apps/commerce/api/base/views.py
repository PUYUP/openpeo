from apps.commerce.models.models import WishList
from django.conf import settings
from django.db import transaction
from django.db.models import Exists, Prefetch, Case, When, Value, BooleanField, Q, F
from django.db.models.expressions import OuterRef, RawSQL, Subquery
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from rest_framework import viewsets, status as response_status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.pagination import LimitOffsetPagination

from utils.generals import get_model
from apps.commerce.utils.permissions import IsCreatorOrReject
from apps.commerce.api.base.serializers import (
    BankSerializer, PaymentBankSerializer, ProductSerializer,
    DeliveryAddressSerializer, ProductAttachmentSerializer
)

Bank = get_model('commerce', 'Bank')
PaymentBank = get_model('commerce', 'PaymentBank')
Product = get_model('commerce', 'Product')
ProductAttachment = get_model('commerce', 'ProductAttachment')
DeliveryAddress = get_model('commerce', 'DeliveryAddress')

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


class BankApiView(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def list(self, request, format=None):
        context = {'request': request}
        queryset = Bank.objects.filter(is_active=True)
        serializer = BankSerializer(queryset, many=True, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)


class PaymentBankApiView(viewsets.ViewSet):
    lookup_field = 'uuid'
    permission_classes = (IsAuthenticated,)
    permission_action = {
        'list': [IsAuthenticated],
        'create': [IsAuthenticated],
        'partial_update': [IsAuthenticated, IsCreatorOrReject],
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
        user_uuid = request.user.uuid
        seller_uuid = request.query_params.get('seller_uuid')
        if seller_uuid:
            user_uuid = seller_uuid

        queryset = PaymentBank.objects \
            .prefetch_related(Prefetch('user'), Prefetch('bank')) \
            .select_related('user', 'bank') \
            .filter(is_active=True, user__uuid=user_uuid)
        
        serializer = PaymentBankSerializer(queryset, many=True, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)

    @method_decorator(never_cache)
    @transaction.atomic
    def create(self, request, format=None):
        context = {'request': request}
        serializer = PaymentBankSerializer(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            try:
                serializer.save()
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    @method_decorator(never_cache)
    @transaction.atomic
    def partial_update(self, request, uuid=None, format=None):
        context = {'request': request}

        # single object
        try:
            queryset = PaymentBank.objects.select_for_update().get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        serializer = PaymentBankSerializer(queryset, data=request.data, partial=True, context=context)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    @method_decorator(never_cache)
    @transaction.atomic
    def destroy(self, request, uuid=None, format=None):
        context = {'request': request}

        # single object
        try:
            queryset = PaymentBank.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        # execute delete
        queryset.delete()
        return Response({'detail': _("Delete success!")}, status=response_status.HTTP_204_NO_CONTENT)


class ProductApiView(viewsets.ViewSet):
    lookup_field = 'uuid'
    permission_classes = (IsAuthenticated,)
    permission_action = {
        'list': [AllowAny],
        'retrieve': [AllowAny],
        'create': [IsAuthenticated],
        'partial_update': [IsAuthenticated, IsCreatorOrReject],
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
        user_uuid = request.query_params.get('user_uuid')
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        radius = request.query_params.get('radius')
        s = request.query_params.get('s')
        is_wishlist = request.query_params.get('is_wishlist', '0')
        is_active = request.query_params.get('is_active', '0')

        wishlist = WishList.objects \
            .prefetch_related(Prefetch('product'), Prefetch('user')) \
            .select_related('product', 'user') \
            .filter(product_id=OuterRef('id'), user_id=request.user.id)

        queryset = Product.objects \
            .prefetch_related(Prefetch('user'), Prefetch('product_attachments')) \
            .annotate(
                is_wishlist=Exists(wishlist),
                wishlist_uuid=Subquery(wishlist.values('uuid')[:1])
            ) \
            .select_related('user')

        if user_uuid:
            queryset = queryset.filter(user__uuid=user_uuid)
        else:
            if request.user.is_authenticated:
                queryset = queryset.exclude(Q(user__uuid=request.user.uuid))

        if is_wishlist == '1':
            queryset = queryset.filter(is_wishlist=True)

        if is_active == '1':
            queryset = queryset.filter(is_active=True)

        # distance
        if latitude and longitude and radius:
            queryset = queryset.annotate(
                distance=RawSQL(
                    '''
                    3959 * acos( cos( radians(%s) )
                    * cos( radians( latitude ) )
                    * cos( radians( longitude ) - radians(%s) )
                    + sin( radians(%s) ) * sin( radians( latitude ) ) )
                    ''',
                    (latitude, longitude, latitude,)
                )
            ) \
            .filter(distance__lte=radius) \
            .order_by('distance')

        # search
        if s:
            queryset = queryset.filter(name__icontains=s)

        queryset_paginator = _PAGINATOR.paginate_queryset(queryset, request)
        serializer = ProductSerializer(queryset_paginator, many=True, context=context)
        return paginate_response(serializer)

    @method_decorator(never_cache)
    @transaction.atomic
    def create(self, request, format=None):
        context = {'request': request}
        serializer = ProductSerializer(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            try:
                serializer.save()
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    @method_decorator(never_cache)
    @transaction.atomic
    def partial_update(self, request, uuid=None, format=None):
        context = {'request': request}

        # single object
        try:
            queryset = Product.objects.select_for_update().get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        serializer = ProductSerializer(queryset, data=request.data, partial=True, context=context)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, uuid=None, format=None):
        context = {'request': self.request, 'is_single': True}

        # single object
        try:
            queryset = Product.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        serializer = ProductSerializer(queryset, many=False, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)

    @method_decorator(never_cache)
    @transaction.atomic
    def destroy(self, request, uuid=None, format=None):
        context = {'request': request}

        # single object
        try:
            queryset = Product.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        # execute delete
        queryset.delete()
        return Response({'detail': _("Delete success!")}, status=response_status.HTTP_204_NO_CONTENT)

    """***********
    ATTACHMENT
    ***********"""
    # LIST, CREATE
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['get', 'post', 'patch'], detail=True,
            permission_classes=[IsAuthenticated],
            url_path='attachments', url_name='view_attachment')
    def view_attachment(self, request, uuid=None):
        """
        Params:
            {
                "title": "string", [required]
                "attach_file": "file" [required]
            }
        """
        context = {'request': request}
        method = request.method
        user = request.user

        if method == 'POST':
            try:
                product_obj = Product.objects.get(uuid=uuid)
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
            except ObjectDoesNotExist:
                raise NotFound(_("Product not found"))

            context['product'] = product_obj
            serializer = ProductAttachmentSerializer(data=request.data, context=context)
            if serializer.is_valid(raise_exception=True):
                try:
                    serializer.save()
                except ValidationError as e:
                    return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
                return Response(serializer.data, status=response_status.HTTP_200_OK)
            return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

        elif method == 'GET':
            queryset = ProductAttachment.objects.annotate(
                is_creator=Case(
                    When(Q(product__user__uuid=user.uuid), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                )
            ) \
            .prefetch_related(Prefetch('product'), Prefetch('product__user')) \
            .select_related('product', 'product__user') \
            .filter(product__uuid=uuid)

            serializer = ProductAttachmentSerializer(queryset, many=True, context=context)
            return Response(serializer.data, status=response_status.HTTP_200_OK)

    # UPDATE, DELETE
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['patch', 'delete'], detail=True,
            permission_classes=[IsAuthenticated],
            parser_classes=[MultiPartParser],
            url_path='attachments/(?P<attachment_uuid>[^/.]+)', 
            url_name='view_attachment_update')
    def view_attachment_update(self, request, uuid=None, attachment_uuid=None):
        """
        Params:
            {
                "title": "string",
                "attach_file": "file"
            }
        """
        context = {'request': request}
        method = request.method

        try:
            queryset = ProductAttachment.objects.select_for_update().get(uuid=attachment_uuid)
        except ValidationError as e:
            return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        if method == 'PATCH':
            serializer = ProductAttachmentSerializer(queryset, data=request.data, partial=True, context=context)
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


class DeliveryAddressApiView(viewsets.ViewSet):
    lookup_field = 'uuid'
    permission_classes = (IsAuthenticated,)
    permission_action = {
        'list': [IsAuthenticated],
        'create': [IsAuthenticated],
        'partial_update': [IsAuthenticated, IsCreatorOrReject],
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
        queryset = DeliveryAddress.objects \
            .prefetch_related(Prefetch('user')) \
            .select_related('user') \
            .filter(user__uuid=request.user.uuid)

        serializer = DeliveryAddressSerializer(queryset, many=True, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)

    @method_decorator(never_cache)
    @transaction.atomic
    def create(self, request, format=None):
        context = {'request': request}
        serializer = DeliveryAddressSerializer(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            try:
                serializer.save()
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, uuid=None, format=None):
        context = {'request': self.request}

        # single object
        try:
            queryset = DeliveryAddress.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        serializer = DeliveryAddressSerializer(queryset, many=False, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)

    @method_decorator(never_cache)
    @transaction.atomic
    def partial_update(self, request, uuid=None, format=None):
        context = {'request': request}

        # single object
        try:
            queryset = DeliveryAddress.objects.select_for_update().get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        serializer = DeliveryAddressSerializer(queryset, data=request.data, partial=True, context=context)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    @method_decorator(never_cache)
    @transaction.atomic
    def destroy(self, request, uuid=None, format=None):
        context = {'request': request}

        # single object
        try:
            queryset = DeliveryAddress.objects.get(uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        # check permission
        self.check_object_permissions(request, queryset)

        # execute delete
        queryset.delete()
        return Response({'detail': _("Delete success!")}, status=response_status.HTTP_204_NO_CONTENT)
