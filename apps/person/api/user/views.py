from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Prefetch, Q, Case, When, Value
from django.utils.translation import ugettext_lazy as _
from django.utils.decorators import method_decorator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError,
    MultipleObjectsReturned
)
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login, logout
from django.core.validators import validate_email
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator

# THIRD PARTY
from rest_framework import status as response_status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, NotAcceptable
from rest_framework.pagination import LimitOffsetPagination

# JWT
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)

# SERIALIZERS 
from apps.person.api.user.serializers import (
    UserFactorySerializer,
    AccountSerializer
)
from apps.person.api.profile.serializers import ProfileSerializer

# GET MODELS FROM GLOBAL UTILS
from utils.generals import get_model
from utils.validators import is_valid_uuid
from apps.person.utils.permissions import IsCurrentUserOrReject
from apps.person.utils.auth import validate_username
from apps.person.utils.constants import PASSWORD_RECOVERY

User = get_model('person', 'User')
Account = get_model('person', 'Account')
Profile = get_model('person', 'Profile')
OTPFactory = get_model('person', 'OTPFactory')

# Define to avoid used ...().paginate__
_PAGINATOR = LimitOffsetPagination()


class UserApiView(viewsets.ViewSet):
    """
    PATCH
    ------

        {
            "gender": "slug",
            "birthdate": "date",
            "biography": "text",
            "picture": "image file"
        }
    """
    otp_email = None
    otp_msisdn = None
    otp_token = None

    # this part of DRF
    lookup_field = 'uuid'
    permission_classes = (AllowAny,)
    permission_action = {
        'list': [IsAuthenticated],
        'retrieve': [IsAuthenticated],
        'partial_update': [IsAuthenticated, IsCurrentUserOrReject],
    }

    def get_permissions(self):
        """
        Instantiates and returns
        the list of permissions that this view requires.
        """
        try:
            # return permission_classes depending on `action`
            return [permission() for permission in self.permission_action
                    [self.action]]
        except KeyError:
            # action is not set return default permission_classes
            return [permission() for permission in self.permission_classes]

    # Get a objects
    def get_object(self, uuid=None, is_update=False):
        # Single object
        if uuid:
            try:
                queryset = User.objects
                if is_update:
                    return queryset.select_for_update().get(uuid=uuid)
                return queryset.get(uuid=uuid)
            except ObjectDoesNotExist:
                raise NotFound()

        # All objects
        return User.objects.prefetch_related(Prefetch('account'), Prefetch('profile')) \
            .select_related('account', 'profile') \
            .all()

    # Return a response
    def get_response(self, serializer, serializer_parent=None):
        response = dict()
        response['count'] = _PAGINATOR.count
        response['per_page'] = settings.PAGINATION_PER_PAGE
        response['navigate'] = {
            'offset': _PAGINATOR.offset,
            'limit': _PAGINATOR.limit,
            'previous': _PAGINATOR.get_previous_link(),
            'next': _PAGINATOR.get_next_link(),
        }
        response['results'] = serializer.data
        return Response(response, status=response_status.HTTP_200_OK)

    # All Users
    def list(self, request, format=None):
        context = {'request': self.request}
        queryset = self.get_object()
        queryset_paginator = _PAGINATOR.paginate_queryset(queryset, request)
        serializer = UserFactorySerializer(queryset_paginator, many=True, context=context,
                                           fields=('uuid', 'username', 'url', 'profile'))
        return self.get_response(serializer)

    # Single User
    def retrieve(self, request, uuid=None, format=None):
        context = {'request': self.request}
        queryset = self.get_object(uuid=uuid)

        # limit when other user see the user
        fields = ('__all__')
        if str(request.user.uuid) != uuid:
            fields = ('uuid', 'username', 'url', 'profile', 'first_name')

        serializer = UserFactorySerializer(queryset, many=False, context=context,
                                           fields=fields)
        return Response(serializer.data, status=response_status.HTTP_200_OK)

    # Get otp object
    def get_otp(self, challenge=None):
        try:
            obj = OTPFactory.objects.select_for_update() \
                .get_verified_unused(email=self.otp_email, msisdn=self.otp_msisdn,
                                     token=self.otp_token, challenge=challenge)
            return obj
        except ObjectDoesNotExist:
            return Response({'detail': _(u"Kode OTP tidak ditemukan.")},
                            status=response_status.HTTP_404_NOT_FOUND)

    # Register User
    @method_decorator(never_cache)
    @transaction.atomic
    def create(self, request, format=None):
        context = {'request': self.request}
        serializer = UserFactorySerializer(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            try:
                serializer.save()
            except ValidationError as e:
                return Response({'detail': e.message}, status=response_status.HTTP_406_NOT_ACCEPTABLE)
            return Response(serializer.data, status=response_status.HTTP_201_CREATED)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    # Update basic user data
    @method_decorator(never_cache)
    @transaction.atomic
    def partial_update(self, request, uuid=None, format=None):
        context = {'request': self.request}

        # Single object
        instance = self.get_object(uuid=uuid, is_update=True)

        serializer = UserFactorySerializer(instance, data=request.data, partial=True, context=context)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=response_status.HTTP_200_OK)
        return Response(serializer.errors, status=response_status.HTTP_400_BAD_REQUEST)

    # Sub-action check email available
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['post'], detail=False, permission_classes=[AllowAny],
            url_path='check-email-available', url_name='view_check_email_available')
    def view_check_email_available(self, request):
        """
        Params:

            {
                "email": "my@email.com"
            }
        """
        data = request.data
        email = data.get('email', None)
        if not email:
            raise NotFound(_(u"Email not provided."))

        try:
            validate_email(email)
        except ValidationError as e:
            raise NotAcceptable({'detail': _(u" ".join(e.messages))})

        try:
            Account.objects.get(Q(user__account__email=Case(When(user__account__email__isnull=False, then=Value(email))))
                                | Q(email=Case(When(email__isnull=False, then=Value(email)))),
                                email_verified=True)

            raise NotAcceptable(_(u"Email `{email}` sudah terdaftar."
                                  " Jika ini milik Anda hubungi kami.".format(email=email)))
        except MultipleObjectsReturned:
            raise NotAcceptable(_(u"Email `{email}` terdaftar lebih dari satu akun. Jika merasa belum pernah mendaftar"
                                  " dengan email tersebut silahkan hubungi kami.".format(email=email)))
        except ObjectDoesNotExist:
            # Check the email has been used in OTP
            check = OTPFactory.objects.filter(email=email, is_used=False, is_expired=False)
            return Response({'detail': _(u"Email tersedia!"), 'is_exist': check.exists(), 'email': email},
                            status=response_status.HTTP_200_OK)

    # Sub-action check msisdn available
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['post'], detail=False, permission_classes=[AllowAny],
            url_path='check-msisdn-available', url_name='view_check_msisdn_available')
    def view_check_msisdn_available(self, request):
        """
        Params:

            {
                "msisdn": "1234567890"
            }
        """
        data = request.data
        msisdn = data.get('msisdn', None)
        if not msisdn:
            raise NotFound(_(u"Masukkan MSISDN."))

        try:
            Account.objects.get(msisdn=msisdn, msisdn_verified=True)
            raise NotAcceptable(_(u"MSISDN `{msisdn}` sudah digunakan."
                                  " Jika ini milik Anda hubungi kami.".format(msisdn=msisdn)))
        except MultipleObjectsReturned:
            raise NotAcceptable(_(u"MSISDN `{msisdn}` terdaftar lebih dari satu akun. Jika merasa belum pernah mendaftar"
                                  " dengan msisdn tersebut silahkan hubungi kami.".format(msisdn=msisdn)))
        except ObjectDoesNotExist:
            # Check whether the msisdn has been used
            check = OTPFactory.objects.filter(msisdn=msisdn, is_used=False, is_expired=False)
            return Response({'detail': _(u"MSISDN tersedia!"), 'is_exist': check.exists(), 'msisdn': msisdn},
                            status=response_status.HTTP_200_OK)

    # Sub-action check account available
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['post'], detail=False, permission_classes=[AllowAny],
            url_path='check-account', url_name='view_check_account')
    def view_check_account(self, request):
        """
        Params:

            {
                "account": "my@email.com / username / msisdn"
            }
        """
        data = request.data
        account = data.pop('account', None)
        if not account:
            raise NotFound(_(u"Masukkan email, nama pengguna atau MSISDN."))

        try:
            user = User.objects.get(Q(username=account)
                                    | Q(email=account) & Q(account__email_verified=True)
                                    | Q(account__msisdn=account) & Q(account__msisdn_verified=True))

            return Response({'detail': _(u"Akun tersedia!"), 'email': user.email, 'msisdn': user.account.msisdn},
                            status=response_status.HTTP_200_OK)
        except MultipleObjectsReturned:
            raise NotAcceptable(_(u"Akun `{account}` sudah digunakan.".format(account=account)))
        except ObjectDoesNotExist:
            raise NotFound({'detail': _(u"Akun `{account}` tidak ditemukan.".format(account=account))})

    # Sub-action check email available
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['post'], detail=False, permission_classes=[AllowAny],
            url_path='check-username-available', url_name='view_check_username_available')
    def view_check_username_available(self, request):
        """
        Params:

            {
                "username": "string"
            }
        """
        data = request.data
        username = data.get('username', None)
        if not username:
            raise NotFound(_(u"Masukkan nama pengguna."))
        
        # check a username is valid string
        try:
            validate_username(username)
        except ValidationError as e:
            raise NotAcceptable({'detail': _(" ".join(e.messages))})

        if User.objects.filter(username=username).exists():
            raise NotAcceptable({'detail': _(u"Nama pengguna `{username}` "
                                             "sudah digunakan.".format(username=username))})
        return Response({'detail': _(u"Nama pengguna tersedia!")},
                        status=response_status.HTTP_200_OK)

    # Sub-action update Profile
    @method_decorator(never_cache)
    @transaction.atomic
    @action(detail=True, methods=['get', 'patch'],
            permission_classes=[IsAuthenticated, IsCurrentUserOrReject],
            url_path='profile', url_name='view_profile')
    def view_profile(self, request, uuid=None):
        context = {'request': self.request}
        try:
            queryset = Profile.objects.get(user__uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        if request.method == 'PATCH':
            serializer = ProfileSerializer(queryset, data=request.data,
                                           partial=True, context=context)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=response_status.HTTP_200_OK)

        if request.method == 'GET':
            serializer = ProfileSerializer(queryset, many=False, context=context)
            return Response(serializer.data, status=response_status.HTTP_200_OK)

    # Sub-action update Account
    # This account need verification
    @method_decorator(never_cache)
    @transaction.atomic
    @action(detail=True, methods=['get', 'patch'],
            permission_classes=[IsAuthenticated, IsCurrentUserOrReject],
            url_path='account', url_name='view_account')
    def view_account(self, request, uuid=None):
        context = {'request': self.request}
        try:
            queryset = Account.objects.get(user__uuid=uuid)
        except ObjectDoesNotExist:
            raise NotFound()

        if request.method == 'PATCH':
            serializer = AccountSerializer(queryset, data=request.data,
                                           partial=True, context=context)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=response_status.HTTP_200_OK)

        if request.method == 'GET':
            serializer = AccountSerializer(queryset, many=False, context=context)
            return Response(serializer.data, status=response_status.HTTP_200_OK)

    # Password recovery as guest
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['post'], detail=False, permission_classes=[AllowAny],
            url_path='password-recovery', url_name='view_password_recovery')
    def view_password_recovery(self, request):
        """
        Params:

            {
                "email": "string",
                "msisdn": "string";
                "token": "string",
                "password1": "string",
                "password2": "string",
                "recovery_token": "string",
                "recovery_uidb64": "string"
            }
        """
        self.otp_email = request.data.get('email')
        self.otp_msisdn = request.data.get('msisdn')
        self.otp_token = request.data.get('token')
        password1 = request.data.get('password1')
        password2 = request.data.get('password2')
        recovery_uidb64 = request.data.get('recovery_uidb64')
        recovery_token = request.data.get('recovery_token')

        # Get otp
        self.otp_obj = self.get_otp(challenge=PASSWORD_RECOVERY)

        # check password confirmation
        if password1 and password2:
            if password1 != password2:
                raise NotAcceptable({'detail': _(u"Kata sandi tidak sama.")})
        else:
            raise NotAcceptable({'detail': _(u"Kata sandi tidak boleh kosong.")})

        # validate password
        try:
            validate_password(password2)
        except ValidationError as e:
            raise NotAcceptable({'detail': ' '.join(e.messages)})

        # check password recovery valid or not
        uid = urlsafe_base64_decode(recovery_uidb64).decode()
        try:
            user = User._default_manager.get(pk=uid)
        except ObjectDoesNotExist:
            raise NotAcceptable({'detail': _(u"Akun tidak ditemukan.")})

        isvalid = default_token_generator.check_token(user, recovery_token)
        if not isvalid:
            raise NotAcceptable({'detail': _(u"Token invalid.")})

        # mark otp used
        self.otp_obj.mark_used()

        # set password
        user.set_password(password2)
        user.save()

        return Response({'detail': _(u"Kata sandi berhasil diperbarui. "
                                     "Silahkan masuk dengan kata sandi baru.")},
                        status=response_status.HTTP_200_OK)

    # Sub-action logout!
    @method_decorator(never_cache)
    @transaction.atomic
    @action(methods=['post'], detail=True, permission_classes=[IsAuthenticated, IsCurrentUserOrReject],
            url_path='logout', url_name='view_logout')
    def view_logout(self, request, uuid=None):
        logout(request)
        return Response({'detail': _(u"Logout!")}, status=response_status.HTTP_204_NO_CONTENT)


class TokenObtainPairSerializerExtend(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user:
            request = self.context.get('request')
            picture = self.user.profile.picture
            picture_url = None
            if picture:
                picture_url = request.build_absolute_uri(picture.url)
    
            data['picture_url'] = picture_url
            data['id'] = self.user.id
            data['uuid'] = self.user.uuid
            data['username'] = self.user.username
            data['first_name'] = self.user.first_name
            data['email'] = self.user.email
            data['msisdn'] = self.user.account.msisdn
        return data


class TokenObtainPairViewExtend(TokenObtainPairView):
    serializer_class = TokenObtainPairSerializerExtend

    @method_decorator(never_cache)
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        # Make user logged-in
        if settings.LOGIN_WITH_JWT:
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
        return Response(serializer.validated_data, status=response_status.HTTP_200_OK)
