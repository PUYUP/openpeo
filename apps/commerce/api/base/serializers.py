import os

from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from rest_framework import serializers
from rest_framework.exceptions import NotAcceptable

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


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)

        # Instantiate the superclass normally
        super(DynamicFieldsModelSerializer, self).__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


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


class ProductSerializer(DynamicFieldsModelSerializer):
    user = serializers.HiddenField(default=CurrentUserDefault())
    url = serializers.HyperlinkedIdentityField(view_name='commerce:product-detail',
                                               lookup_field='uuid', read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

    def validate(self, data):
        order_deadline = data.get('order_deadline')
        delivery_date = data.get('delivery_date')

        if delivery_date.date() <= order_deadline.date():
            raise NotAcceptable(detail=_("Waktu pengiriman tidak boleh kurang dari waktu pengiriman"))
        return data

    def validate_order_deadline(self, value):
        if value.date() < timezone.now().date():
            raise NotAcceptable(detail=_("Waktu pemesanan tidak boleh kemarin"))
        return value

    def to_representation(self, instance):
        request = self.context.get('request')
        is_single = self.context.get('is_single')
        ret = super().to_representation(instance)

        first_name = instance.user.first_name
        attachment_url = None
        attachment = instance.product_attachments.first()
        if attachment:
            attachment_url = request.build_absolute_uri(attachment.attach_file.url)

        # show only on single object
        if is_single:
            product_type = ContentType.objects.get_for_model(instance)
            ret['content_type_id'] = product_type.id

        ret['seller_name'] = first_name if first_name else instance.user.username
        ret['seller_id'] = instance.user.id
        ret['picture'] = attachment_url
        return ret

    @transaction.atomic
    def create(self, validated_data):
        obj = Product.objects.create(**validated_data)
        return obj


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
        print(attach_file)
        obj = ProductAttachment.objects.create(product_id=product.id, **validated_data)
        handle_upload_attachment(obj, attach_file)
        return obj
