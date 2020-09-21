from django.db import transaction, IntegrityError
from django.db.models import Prefetch, Value, F
from django.core.exceptions import ObjectDoesNotExist
from django.http import request
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from rest_framework import serializers
from rest_framework.exceptions import NotAcceptable

from utils.generals import get_model
from apps.person.utils.auth import CurrentUserDefault
from apps.commerce.utils.constants import CONFIRMED, DONE, PENDING, DELIVER

Cart = get_model('commerce', 'Cart')
CartItem = get_model('commerce', 'CartItem')
Order = get_model('commerce', 'Order')
OrderItem = get_model('commerce', 'OrderItem')
Product = get_model('commerce', 'Product')


class CartItemListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        request = self.context.get('request')
        if data.exists():
            data = data.prefetch_related(Prefetch('product'), Prefetch('product__user'), Prefetch('product__product_attachments')) \
                .select_related('product', 'product__user') \
                .annotate(subtotal=F('product__price') * F('quantity'))
        return super().to_representation(data)


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        list_serializer_class = CartItemListSerializer
        model = CartItem
        exclude = ('cart',)

    def to_representation(self, instance):
        request = self.context.get('request')
        ret = super().to_representation(instance)

        subtotal = getattr(instance, 'subtotal', None)
        attachment_url = None
        attachment = instance.product.product_attachments.first()
        if attachment:
            attachment_url = request.build_absolute_uri(attachment.attach_file.url)

        ret['product_name'] = instance.product.name
        ret['picture'] = attachment_url

        if subtotal:
            ret['subtotal'] = subtotal
        return ret


class CartSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())
    url = serializers.HyperlinkedIdentityField(view_name='commerce:cart-detail',
                                               lookup_field='uuid', read_only=True)
    cart_items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = '__all__'

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        first_name = instance.seller.first_name

        ret['seller_name'] = first_name if first_name else instance.seller.username
        ret['seller_id'] = instance.seller.id
        return ret

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        create_items = list()
        update_items = list()
        cart_items = validated_data.pop('cart_items', None)

        # no items reject
        if not cart_items:
            raise NotAcceptable(detal=_("Tidak ada produk"))

        for item in cart_items:
            product = item.get('product')
            
            # check order date overdue
            if timezone.now().date() > product.order_deadline.date():
                raise NotAcceptable(detail=_("Batas waktu pemesanan terlewati"))
                break

            # check current user is creator of product
            if request.user.id == product.user.id:
                raise NotAcceptable(detail=_("Tidak bisa membeli produk sendiri"))
                break

        cart, cart_created = Cart.objects.update_or_create(
            user_id=request.user.id,
            is_done=False,
            **validated_data
        )

        # prepare items
        for item in cart_items:
            try:
                item_obj = CartItem.objects.get(cart_id=cart.id, product_id=item.get('product'))
            except ObjectDoesNotExist:
                item_obj = None

            if item_obj:
                quantity = item.get('quantity')

                # update if quantity defined
                # if not delete cart item
                if quantity and quantity > 0:
                    setattr(item_obj, 'quantity', quantity)
                    setattr(item_obj, 'note', item.get('note'))

                    update_items.append(item_obj)
                else:
                    item_obj.delete()
            else:
                oi = CartItem(cart=cart, **item)
                create_items.append(oi)

        # create all items
        if create_items:
            try:
                CartItem.objects.bulk_create(create_items)
            except IntegrityError as e:
                pass

        # Update item
        if update_items:
            try:
                CartItem.objects.bulk_update(update_items, ['quantity', 'note'])
            except IntegrityError as e:
                pass

        return cart


class OrderItemListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        request = self.context.get('request')
        if data.exists():
            data = data.prefetch_related(Prefetch('product'), Prefetch('product__user'), Prefetch('product__product_attachments')) \
                .select_related('product', 'product__user') \
                .annotate(subtotal=F('product__price') * F('quantity'))
        return super().to_representation(data)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        list_serializer_class = OrderItemListSerializer
        model = OrderItem
        exclude = ('order',)

    def validate_status(self, value):
        instance = self.instance
        if instance:
            if value == CONFIRMED:
                if instance.status != PENDING:
                    raise serializers.ValidationError(_("Status sudah %s" % instance.get_status_display()))

            if value == DELIVER:
                if instance.status != CONFIRMED:
                    raise serializers.ValidationError(_("Status sudah %s" % instance.get_status_display()))
            
            if value == DONE:
                if instance.status != DELIVER:
                    raise serializers.ValidationError(_("Status sudah %s" % instance.get_status_display()))

        return value

    def to_representation(self, instance):
        request = self.context.get('request')
        ret = super().to_representation(instance)

        subtotal = getattr(instance, 'subtotal', None)
        attachment_url = None
        attachment = instance.product.product_attachments.first()
        if attachment:
            attachment_url = request.build_absolute_uri(attachment.attach_file.url)

        ret['product_name'] = instance.product.name
        ret['picture'] = attachment_url

        if subtotal:
            ret['subtotal'] = subtotal
        return ret


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())
    total_item = serializers.IntegerField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='commerce:order-detail',
                                               lookup_field='uuid', read_only=True)

    class Meta:
        model = Order
        fields = '__all__'

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        first_name = instance.seller.first_name
        items_summary = instance.cart.cart_items.values_list('product__name', flat=True)
        first_item = instance.cart.cart_items.first()

        ret['seller_name'] = first_name if first_name else instance.seller.username
        ret['seller_uuid'] = instance.seller.uuid
        ret['items_summary'] = items_summary
        ret['delivery_date'] = first_item.product.delivery_date if hasattr(first_item, 'product') else None

        return ret

    @transaction.atomic
    def create(self, validated_data):
        obj = Order.objects.create(**validated_data)
        return obj


class OrderDetailSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = '__all__'

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        first_name = instance.seller.first_name

        ret['seller_name'] = first_name if first_name else instance.seller.username
        ret['seller_uuid'] = instance.seller.uuid
        return ret


class SellProductSerializer(serializers.ModelSerializer):
    total = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='commerce:sell-detail',
                                               lookup_field='uuid', read_only=True)

    class Meta:
        model = Product
        fields = '__all__'


class SellItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        buyer_name = instance.order.user.first_name
        buyer_username = instance.order.user.username
        buyer_msisdn = instance.order.user.account.msisdn
        product_type = ContentType.objects.get_for_model(instance.product)
        address = instance.order.user.address.address

        ret['buyer_id'] = instance.order.user.id
        ret['buyer_name'] = buyer_name if buyer_name else buyer_username
        ret['buyer_msisdn'] = buyer_msisdn
        ret['buyer_address'] = address
        ret['order_uuid']  = instance.order.uuid
        ret['product_content_type_id'] = product_type.id
        return ret
