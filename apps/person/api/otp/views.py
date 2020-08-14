from django.conf import settings
from django.db import transaction
from django.views.decorators.cache import never_cache
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.decorators import method_decorator
from django.core.validators import validate_email
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Case, When, Value
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework import status as response_status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, NotAcceptable

from utils.generals import get_model, random_string
from apps.person.utils.constants import (
    REGISTER_VALIDATION,
    PASSWORD_RECOVERY,
    OTP_SESSION_FIELDS,
    CHANGE_EMAIL,
    CHANGE_EMAIL_VALIDATION,
    CHANGE_MSISDN,
    CHANGE_MSISDN_VALIDATION,
    CHANGE_PASSWORD,
    CHANGE_USERNAME
)
from apps.person.api.otp.serializers import OTPFactoryFactorySerializer
from apps.person.utils.auth import get_users_by_email

OTPFactory = get_model('person', 'OTPFactory')


class OTPFactoryApiView(viewsets.ViewSet):
    """
    Param:

        {
            "email": "my@email.com",
            "msisdn": "09284255",
            "challenge": "email_validation"
        }
    
    Rules:

        If email provided, msisdn not required
        If msisdn provide, email not required
    """
    lookup_field = 'uuid'
    permission_classes = (AllowAny,)

    @method_decorator(never_cache)
    @transaction.atomic
    def create(self, request, format=None):
        context = {'request': request}
        serializer = OTPFactoryFactorySerializer(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            try:
                serializer.save()
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)

            # response based on new or updated object
            rs = response_status.HTTP_200_OK
            if serializer.data.get('created', False):
                rs = response_status.HTTP_201_CREATED
    
            return Response(serializer.data, status=rs)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    @method_decorator(never_cache)
    @transaction.atomic
    def partial_update(self, request, uuid=None):
        context = {'request': self.request}
    
        try:
            email = request.data.get('email', None)
            msisdn = request.data.get('msisdn', None)

            instance = OTPFactory.objects.select_for_update() \
                .get_unverified_unused(email=email, msisdn=msisdn, uuid=uuid)
        except ValidationError as err:
            raise NotAcceptable(detail=_(' '.join(err.messages)))
        except ObjectDoesNotExist:
            raise NotFound(_("Kode OTP tidak ditemukan."))

        serializer = OTPFactoryFactorySerializer(instance, data=request.data, partial=True,
                                                 context=context)
        if serializer.is_valid(raise_exception=True):
            try:
                serializer.save()
            except ValidationError as e:
                return Response({'detail': _(u" ".join(e.messages))}, status=response_status.HTTP_406_NOT_ACCEPTABLE)

            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    # Sub-action request password reset
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['post'], detail=False, permission_classes=[AllowAny],
            url_path='validate', url_name='validate')
    def validate(self, request):
        """
        Format:

            {
                "email": "string",
                "msisdn": "string",
                "token": "string",
                "passcode": "string",
                "challenge": "string"
            }
        """
        context = {'request': request}
        email = request.data.get('email', None)
        msisdn = request.data.get('msisdn', None)
        challenge = request.data.get('challenge', None)
        token = request.data.get('token', None)
        passcode = request.data.get('passcode', None)

        if (not email and not msisdn) or not challenge or not token or not passcode:
            raise NotAcceptable(_(u"Required parameter not provided."
                                  " Required email or msisdn, challenge, token and code."))

        try:
            if not passcode.isupper():
                passcode = passcode.upper()

            otp_obj = OTPFactory.objects.select_for_update() \
                .get_unverified_unused(email=email, msisdn=msisdn, token=token,
                                       challenge=challenge, passcode=passcode)
        except ObjectDoesNotExist:
            raise NotFound({'detail': _(u"Kode OTP salah atau kadaluarsa.")})

        try:
            otp_obj.validate()
        except ValidationError as e:
            return Response(
                {'detail': _(u" ".join(e.messages))},
                status=response_status.HTTP_403_FORBIDDEN)

        # in case 'request change' some otp need to mark used immediately
        if challenge == CHANGE_EMAIL or challenge == CHANGE_MSISDN:
            otp_obj.mark_used()

        # if password recovery request and user not logged-in
        if not request.user.is_authenticated and challenge == PASSWORD_RECOVERY:
            token = None
            uidb64 = None

            if email:
                users = get_users_by_email(email)
                for user in users:
                    token = default_token_generator.make_token(user)
                    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                    break

            if msisdn:
                # TODO: SMS otp
                pass

            if token and uidb64:
                context['password_recovery_token'] = token
                context['password_recovery_uidb64'] = uidb64

        context['is_validate'] = True
        serializer = OTPFactoryFactorySerializer(otp_obj, many=False, context=context)
        return Response(serializer.data, status=response_status.HTTP_200_OK)
