from django.conf import settings
from django.db import transaction, IntegrityError
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import EmailValidator

from rest_framework import serializers
from rest_framework.reverse import reverse

# PROJECT UTILS
from utils.generals import get_model
from apps.person.utils.constants import (
    CHANGE_EMAIL_VALIDATION, CHANGE_MSISDN_VALIDATION,
    REGISTER_VALIDATION
)
from apps.person.api.validator import (
    EmailDuplicateValidator,
    EmailVerifiedForRegistrationValidator,
    MSISDNDuplicateValidator,
    MSISDNVerifiedForRegistrationValidator,
    MSISDNNumberValidator,
    PasswordValidator
)
from apps.person.api.account.serializers import AccountSerializer
from apps.person.api.profile.serializers import ProfileSerializer

User = get_model('person', 'User')
Account = get_model('person', 'Account')
OTPFactory = get_model('person', 'OTPFactory')


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

        if fields is not None and fields != '__all__':
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class UserFactorySerializer(DynamicFieldsModelSerializer, serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='person:user-detail',
                                               lookup_field='uuid', read_only=True)

    profile = ProfileSerializer(many=False, read_only=True)
    account = AccountSerializer(many=False, read_only=True)

    # for registration only
    # msisdn not part of User model
    # msisdn part of Account
    msisdn = serializers.CharField(required=False, write_only=True,
                                   validators=[MSISDNNumberValidator()],
                                   min_length=8, max_length=14)

    class Meta:
        model = User
        exclude = ('id', 'user_permissions', 'groups', 'date_joined',
                   'is_superuser', 'last_login', 'is_staff',)
        extra_kwargs = {
            'password': {
                'write_only': True,
                'min_length': 6
            },
            'username': {
                'min_length': 4,
                'max_length': 15
            },
            'email': {
                'required': False,
                'validators': [EmailValidator()]
            }
        }

    def __init__(self, *args, **kwargs):
        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        # default otp
        self.otp_obj = None

        # data
        data = kwargs.get('data', dict())
        self.email = data.get('email', None)
        self.msisdn = data.get('msisdn', None)
        
        # used for password change only
        self.password = data.get('password', None)
        self.new_password1 = data.get('new_password1', None)
        self.new_password2 = data.get('new_password2', None)

        # remove password validator if update
        if self.instance and self.new_password1 and self.new_password2:
            pass
        else:
            if 'password' in self.fields:
                self.fields['password'].validators.extend([PasswordValidator()])

        if settings.STRICT_MSISDN and 'msisdn' in self.fields:
            # MSISDN required if EMAIL not provided
            if not self.email:
                self.fields['msisdn'].required = True

            if settings.STRICT_MSISDN_DUPLICATE:
                self.fields['msisdn'].validators.extend([MSISDNDuplicateValidator()])

        if settings.STRICT_EMAIL and 'email' in self.fields:
            # EMAIL required if MSISDN not provided
            if not self.msisdn:
                self.fields['email'].required = True

            if settings.STRICT_EMAIL_DUPLICATE:
                self.fields['email'].validators.extend([EmailDuplicateValidator()])

    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        # set is_active to True
        # if False user can't loggedin
        data['is_active'] = True
        return data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        return ret

    def validate_email(self, value):
        # check verified email
        if settings.STRICT_EMAIL_VERIFIED:
            if self.instance:
                # update user
                with transaction.atomic():
                    try:
                        self.otp_obj = OTPFactory.objects.select_for_update() \
                            .get_verified_unused(email=value, challenge=CHANGE_EMAIL_VALIDATION)
                    except ObjectDoesNotExist:
                        raise serializers.ValidationError(_(u"Kode OTP pembaruan email salah."))
            else:
                # create user
                with transaction.atomic():
                    try:
                        self.otp_obj = OTPFactory.objects.select_for_update() \
                            .get_verified_unused(email=value, challenge=REGISTER_VALIDATION)
                    except ObjectDoesNotExist:
                        raise serializers.ValidationError(_(u"Alamat email belum tervalidasi."))
        return value

    def validate_msisdn(self, value):
        # check msisdn verified
        if settings.STRICT_MSISDN_VERIFIED:
            if self.instance:
                # update user
                with transaction.atomic():
                    try:
                        self.otp_obj = OTPFactory.objects.select_for_update() \
                            .get_verified_unused(msisdn=value, challenge=CHANGE_MSISDN_VALIDATION)
                    except ObjectDoesNotExist:
                        raise serializers.ValidationError(_(u"Kode OTP pembaruan msisdn salah."))
            else:
                # create user
                with transaction.atomic():
                    try:
                        self.otp_obj = OTPFactory.objects.select_for_update() \
                            .get_verified_unused(msisdn=value, challenge=REGISTER_VALIDATION)
                    except ObjectDoesNotExist:
                        raise serializers.ValidationError(_(u"MSISDN belum tervalidasi."))
        return value

    """
    def validate_username(self, value):
        if self.instance:
            email = self.instance.email
            msisdn = self.instance.account.msisdn

            with transaction.atomic():
                try:
                    self.otp_obj = OTPFactory.objects.select_for_update() \
                        .get_verified_unused(email=email, msisdn=msisdn, challenge=CHANGE_USERNAME)
                except ObjectDoesNotExist:
                    raise serializers.ValidationError(_(u"Kode OTP pembaruan nama pengguna salah."))
        return value
    """

    def validate_password(self, value):
        instance = getattr(self, 'instance', dict())
        if instance:
            username = getattr(instance, 'username', None)

            # make sure new and old password filled
            if not self.new_password1 or not self.new_password2:
                raise serializers.ValidationError(_(u"Kata sandi lama dan baru wajib."))

            if self.new_password1 != self.new_password2:
                raise serializers.ValidationError(_(u"Kata sandi lama dan baru tidak sama."))

            try:
                validate_password(self.new_password2)
            except ValidationError as e:
                raise serializers.ValidationError(e.messages)

            # check current password is passed
            passed = authenticate(username=username, password=self.password)
            if passed is None:
                raise serializers.ValidationError(_(u"Kata sandi lama salah."))
            return self.new_password2
        return value

    @transaction.atomic
    def create(self, validated_data):
        self.msisdn = validated_data.pop('msisdn')

        try:
            user = User.objects.create_user(**validated_data)
        except IntegrityError as e:
            raise ValidationError(repr(e))
        except TypeError as e:
            raise ValidationError(repr(e))

        # create Account instance
        if self.msisdn:
            account = getattr(user, 'account')
            if account:
                account.msisdn = self.msisdn
                account.msisdn_verified = True
                account.save()
            else:
                try:
                    Account.objects.create(user=user, msisdn=self.msisdn, msisdn_verified=True)
                except IntegrityError:
                    pass

        # all done mark otp as used
        if self.otp_obj:
            self.otp_obj.mark_used()
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get('request', None)

        for key, value in validated_data.items():
            if hasattr(instance, key):
                # update password
                if key == 'password':
                    instance.set_password(value)

                    # add flash message
                    messages.success(request, _("Kata sandi berhasil dirubah."
                                                " Login dengan kata sandi baru Anda."))
                else:
                    old_value = getattr(instance, key, None)
                    if value and old_value != value:
                        setattr(instance, key, value)
        instance.save()

        # all done mark otp as used
        if self.otp_obj:
            self.otp_obj.mark_used()
        return instance
