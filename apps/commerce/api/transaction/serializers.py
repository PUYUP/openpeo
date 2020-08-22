from django.db import transaction, IntegrityError
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers

from utils.generals import get_model
from apps.person.utils.auth import CurrentUserDefault

Cart = get_model('commerce', 'Cart')
CartItem = get_model('commerce', 'CartItem')


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        exclude = ('cart',)


class CartSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())
    url = serializers.HyperlinkedIdentityField(view_name='commerce:cart-detail',
                                               lookup_field='uuid', read_only=True)
    cart_items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        create_items = list()
        update_items = list()
        cart_items = validated_data.pop('cart_items')
        cart, cart_created = Cart.objects.update_or_create(user_id=request.user.id, **validated_data)

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
