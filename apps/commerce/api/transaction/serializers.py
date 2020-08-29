from django.db import transaction, IntegrityError
from django.db.models import Prefetch, Value, F
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers

from utils.generals import get_model
from apps.person.utils.auth import CurrentUserDefault

Cart = get_model('commerce', 'Cart')
CartItem = get_model('commerce', 'CartItem')
Order = get_model('commerce', 'Order')
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
        cart_items = validated_data.pop('cart_items')
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
        ret['items_summary'] = items_summary
        ret['delivery_date'] = first_item.product.delivery_date if hasattr(first_item, 'product') else None

        return ret


class OrderDetailSerializer(serializers.ModelSerializer):
    cart = CartSerializer(many=False)

    class Meta:
        model = Order
        fields = '__all__'

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        first_name = instance.seller.first_name

        ret['seller_name'] = first_name if first_name else instance.seller.username
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
        model = CartItem
        fields = '__all__'

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        buyer_name = instance.cart.user.first_name
        buyer_username = instance.cart.user.username
        buyer_msisdn = instance.cart.user.account.msisdn

        ret['buyer_name'] = buyer_name if buyer_name else buyer_username
        ret['buyer_msisdn'] = buyer_msisdn
        ret['cart_uuid']  = instance.cart.uuid
        return ret
