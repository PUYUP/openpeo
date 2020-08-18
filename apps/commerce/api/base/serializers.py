from rest_framework import serializers

from utils.generals import get_model
from apps.person.utils.auth import CurrentUserDefault

Bank = get_model('commerce', 'Bank')
PaymentBank = get_model('commerce', 'PaymentBank')
Product = get_model('commerce', 'Product')


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = '__all__'


class PaymentBankSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())

    class Meta:
        model = PaymentBank
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())

    class Meta:
        model = Product
        fields = '__all__'
