import os

from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from utils.generals import get_model
from apps.person.utils.auth import CurrentUserDefault

Bank = get_model('commerce', 'Bank')
PaymentBank = get_model('commerce', 'PaymentBank')
Product = get_model('commerce', 'Product')
ProductAttachment = get_model('commerce', 'ProductAttachment')
DeliveryAddress = get_model('commerce', 'DeliveryAddress')


def handle_upload_attachment(instance, file):
    if instance and file:
        name, ext = os.path.splitext(file.name)

        fsize = file.size / 1000
        if fsize > 5000:
            raise serializers.ValidationError({'detail': _("Ukuran file maksimal 5 MB")})
    
        if ext != '.jpeg' and ext != '.jpg' and ext != '.png':
            raise serializers.ValidationError({'detail': _("Jenis file tidak diperbolehkan")})

        product = getattr(instance, 'product')
        username = product.user.username
        product_name = product.name
        filename = '{username}_{product_name}'.format(username=username, product_name=product_name)
        filename_slug = slugify(filename)

        instance.attach_type = ext
        instance.attach_file.save('%s%s' % (filename_slug, ext), file, save=False)
        instance.save(update_fields=['attach_file', 'attach_type'])


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = '__all__'


class PaymentBankSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())
    bank_name = serializers.CharField(source='bank.name', read_only=True)

    class Meta:
        model = PaymentBank
        fields = '__all__'


class DeliveryAddressSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())
    url = serializers.HyperlinkedIdentityField(view_name='commerce:address-detail',
                                               lookup_field='uuid', read_only=True)

    class Meta:
        model = DeliveryAddress
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())
    url = serializers.HyperlinkedIdentityField(view_name='commerce:product-detail',
                                               lookup_field='uuid', read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

    def to_representation(self, instance):
        request = self.context.get('request')
        ret = super().to_representation(instance)

        first_name = instance.user.first_name
        attachment_url = None
        attachment = instance.product_attachments.first()
        if attachment:
            attachment_url = request.build_absolute_uri(attachment.attach_file.url)

        ret['seller_name'] = first_name if first_name else instance.user.username
        ret['seller_id'] = instance.user.id
        ret['picture'] = attachment_url
        return ret


class ProductAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttachment
        exclude = ('product',)

    def to_representation(self, instance):
        request = self.context.get('request')
        ret = super().to_representation(instance)
        ret['is_creator'] = request.user.uuid == instance.product.user.uuid
        return ret

    @transaction.atomic
    def create(self, validated_data):
        product = self.context['product']
        attach_file = validated_data.pop('attach_file')
        obj = ProductAttachment.objects.create(product_id=product.id, **validated_data)
        handle_upload_attachment(obj, attach_file)
        return obj
