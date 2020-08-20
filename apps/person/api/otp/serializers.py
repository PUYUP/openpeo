from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import NotAcceptable

from utils.generals import get_model
from apps.person.utils.constants import OTP_SESSION_FIELDS, PASSWORD_RECOVERY
from apps.person.utils.auth import get_users_by_email

OTPFactory = get_model('person', 'OTPFactory')


class OTPFactoryFieldsModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        data = kwargs.get('data', None)
        context = kwargs.get('context', None)

        if data:
            email = data.get('email', None)
            msisdn = data.get('msisdn', None)
            request = context.get('request', None)

            if request.method == 'POST' and (not email or not msisdn):
                if email:
                    self.fields.pop('msisdn')
                elif msisdn:
                    self.fields.pop('email')


class OTPFactoryFactorySerializer(OTPFactoryFieldsModelSerializer, serializers.ModelSerializer):
    class Meta:
        model = OTPFactory
        fields = ('uuid', 'email', 'msisdn', 'challenge', 'token',)
        read_only_fields = ('uuid', 'token',)
        extra_kwargs = {
            'challenge': {
                'required': True
            },
            'msisdn': {
                'required': True,
                'min_length': 4,
                'max_length': 15
            },
            'email': {
                'required': True,
                'validators': [EmailValidator()]
            },
        }

    def __init__(self, *args, **kwargs):
        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

    def get_msisdn(self, obj):
        if obj.msisdn:
            return obj.msisdn
        else:
            request = self.context.get('request', None)
            user = request.user
            return user.account.msisdn

    def to_representation(self, instance):
        send_to_message = _("Terjadi kesalahan.")
        if instance.email:
            send_to_message = _("Kode OTP telah dikirimkan melalui email ke <strong>{email}</strong>".format(email=instance.email))

        if instance.msisdn:
            send_to_message = _("Kode OTP telah dikirimkan melalui SMS ke <strong>{msisdn}</strong>".format(msisdn=instance.msisdn))

        # capture data from context params
        request = self.context.get('request', None)
        is_validate = self.context.get('is_validate', False)

        # normalize
        ret = super().to_representation(instance)

        if instance.msisdn:
            ret['msisdn'] = instance.msisdn
        else:
            if request:
                user = request.user
                account = getattr(user, 'account', dict())
                ret['msisdn'] = getattr(account, 'msisdn', None)

        # this data not for validate response
        if not is_validate:
            ret['created'] = getattr(instance, 'created', None)
            ret['send_to_message'] = send_to_message

        # prepare for password recovery
        password_recovery_token = self.context.get('password_recovery_token', None)
        password_recovery_uidb64 = self.context.get('password_recovery_uidb64', None)
        if password_recovery_token and password_recovery_uidb64:
            ret['password_recovery_token'] = password_recovery_token
            ret['password_recovery_uidb64'] = password_recovery_uidb64

        return ret

    def validate(self, attrs):
        instance = OTPFactory(**attrs)
        instance.clean()
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request', None)
        email = validated_data.pop('email', None)
        msisdn = validated_data.pop('msisdn', None)
        challenge = validated_data.pop('challenge', None)

        if not email and not msisdn:
            raise NotAcceptable(_(u"Email or msisdn not provided."))

        _defaults = {
            'challenge': challenge,
            'is_verified': False,
            'is_used': False,
            'is_expired': False,
        }

        if email and not msisdn:
            _defaults['email'] = email

        if msisdn and not email:
            _defaults['msisdn'] = msisdn

        # Ops, please choose one (email or telehone)
        if msisdn and email:
            raise NotAcceptable(_(u"Only accept one of email or msisdn."))

        # If `valid_until` greater than time now we update OTP Code
        obj, created = OTPFactory.objects \
            .filter(Q(valid_until__gt=timezone.now())) \
            .update_or_create(**_defaults, defaults=_defaults) 

        setattr(obj, 'created', created)
        return obj

    @transaction.atomic
    def update(self, instance, validated_data):
        setattr(instance, 'created', False)
        return instance
