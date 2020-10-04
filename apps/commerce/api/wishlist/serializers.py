from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault

from utils.generals import get_model

WishList = get_model('commerce', 'WishList')


class WishListSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())
    url = serializers.HyperlinkedIdentityField(view_name='commerce:wishlist-detail',
                                               lookup_field='uuid', read_only=True)

    class Meta:
        model = WishList
        fields = '__all__'
