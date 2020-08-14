from django.conf import settings
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from rest_framework import serializers

from utils.generals import get_model
from apps.person.utils.constants import CHANGE_MSISDN_VALIDATION
from apps.person.api.validator import (
    MSISDNDuplicateValidator,
    MSISDNNumberValidator
)

Account = get_model('person', 'Account')
Profile = get_model('person', 'Profile')
OTPFactory = get_model('person', 'OTPFactory')


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('picture', 'headline',)


# User account serializer
class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        exclude = ('user', 'id', 'create_date', 'update_date',)
        extra_kwargs = {
            'msisdn': {
                'min_length': 8,
                'max_length': 14,
                'validators': [MSISDNNumberValidator()]
            }
        }
    
    def __init__(self, *args, **kwargs):
        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        # default otp
        self.otp_obj = None

        # data available only on PATCH and POST
        data = kwargs.get('data', None)
        if data:
            if settings.STRICT_MSISDN_DUPLICATE:
                self.fields['msisdn'].validators.extend([MSISDNDuplicateValidator()])

    def validate_msisdn(self, value):
        if self.instance:
            with transaction.atomic():
                try:
                    self.otp_obj = OTPFactory.objects.select_for_update() \
                        .get_verified_unused(msisdn=value, challenge=CHANGE_MSISDN_VALIDATION)
                except ObjectDoesNotExist:
                    raise serializers.ValidationError(_(u"Kode OTP pembaruan msisdn salah."))
        return value

    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        # one field each update request
        if len(data) > 1:
            raise serializers.ValidationError({
                'field': _("Hanya boleh satu data.")
            })

        # field can't empty to
        if len(data) == 0:
            raise serializers.ValidationError({
                'field': _("Tidak ada yang diperbarui.")
            })
        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            if hasattr(instance, key):
                old_value = getattr(instance, key, None)
                if value and old_value != value:
                    setattr(instance, key, value)
        instance.save()

        # all done mark otp used
        self.otp_obj.mark_used()
        return instance
