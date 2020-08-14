from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers

from utils.generals import get_model
from apps.person.utils.constants import REGISTER_VALIDATION

User = get_model('person', 'User')
OTPFactory = get_model('person', 'OTPFactory')


# Password verification
class PasswordValidator(object):
    requires_context = True

    def __call__(self, value, serializer_field):
        validate_password(value)


# Check duplicate email if has verified
class EmailDuplicateValidator(object):
    requires_context = True

    def __call__(self, value, serializer_field):
        user = User.objects \
            .prefetch_related('account') \
            .select_related('account') \
            .filter(email=value, account__email_verified=True)

        if user.exists():
            raise serializers.ValidationError(
                _(u"Email {email} sudah terdaftar.".format(email=value))
            )


# Check email is validate for registration purpose
class EmailVerifiedForRegistrationValidator(object):
    requires_context = True

    def __call__(self, value, serializer_field):
        otp = OTPFactory.objects.filter(challenge=REGISTER_VALIDATION, email=value,
                                        is_used=False, is_verified=True, is_expired=False)

        if not otp.exists():
            raise serializers.ValidationError(_(u"Alamat email belum tervalidasi."))


# Check duplicate msisdn if has verified
class MSISDNDuplicateValidator(object):
    requires_context = True

    def __call__(self, value, serializer_field):
        user = User.objects \
            .prefetch_related('account') \
            .select_related('account') \
            .filter(account__msisdn=value, account__msisdn_verified=True)

        if user.exists():
            raise serializers.ValidationError(_(u"Nomor telepon sudah digunakan."))


# Check msisdn is validate for registration purpose
class MSISDNVerifiedForRegistrationValidator(object):
    requires_context = True

    def __call__(self, value, serializer_field):
        otp = OTPFactory.objects.filter(challenge=REGISTER_VALIDATION, msisdn=value,
                                        is_used=False, is_verified=True, is_expired=False)

        if not otp.exists():
            raise serializers.ValidationError(_(u"Nomor telepon belum tervalidasi."))


# Check duplicate msisdn if has verified
class MSISDNNumberValidator(object):
    requires_context = True

    def __call__(self, value, serializer_field):
        if not value.isnumeric():
            raise serializers.ValidationError(_(u"Nomor telepon hanya boleh angka."))
