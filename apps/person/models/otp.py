import uuid
import pyotp

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models
from django.db.models import Q, F, Prefetch, Case, When, Value
from django.utils.translation import ugettext_lazy as _
from django.core.validators import RegexValidator, ValidationError, validate_email
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from utils.generals import get_model
from utils.validators import non_python_keyword
from apps.person.utils.constants import (
    OTP_CHALLENGE,
    PASSWORD_RECOVERY,
    CHANGE_EMAIL,
    REGISTER_VALIDATION
)

User = get_model('person', 'User')


class OTPFactoryQuerySet(models.query.QuerySet):
    def get_verified_unused(self, email=None, msisdn=None, token=None,
                            challenge=None, uuid=None, passcode=None):
        q_uuid = Q()
        if uuid:
            q_uuid = Q(uuid=uuid)

        q_passcode = Q()
        if passcode:
            q_passcode = Q(passcode=passcode)

        q_token = Q()
        if token:
            q_token = Q(token=token)

        q_challenge = Q()
        if challenge:
            q_challenge = Q(challenge=challenge)

        return self.get(
            Q(email=Case(When(email__isnull=False, then=Value(email))))
            | Q(msisdn=Case(When(msisdn__isnull=False, then=Value(msisdn)))),
            Q(is_verified=True), Q(is_used=False), Q(is_expired=False),
            q_uuid, q_passcode, q_token, q_challenge
        )

    def get_unverified_unused(self, email=None, msisdn=None, token=None,
                              challenge=None, uuid=None, passcode=None):
        q_uuid = Q()
        if uuid:
            q_uuid = Q(uuid=uuid)

        q_passcode = Q()
        if passcode:
            q_passcode = Q(passcode=passcode)

        q_token = Q()
        if token:
            q_token = Q(token=token)

        q_challenge = Q()
        if challenge:
            q_challenge = Q(challenge=challenge)

        return self.get(
            Q(email=Case(When(email__isnull=False, then=Value(email))))
            | Q(msisdn=Case(When(msisdn__isnull=False, then=Value(msisdn)))),
            Q(is_verified=False), Q(is_used=False), Q(is_expired=False),
            q_uuid, q_passcode, q_token, q_challenge
        )


class AbstractOTPFactory(models.Model):
    """
    Send OTP Code with;
        :email
        :msisdn (SMS or Voice Call)

    :valid_until; OTP Code validity max date (default 2 hour)
    :is_expired; expired
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             null=True, blank=True, related_name='otps',
                             related_query_name='otp')

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    create_date = models.DateTimeField(auto_now_add=True, null=True)
    update_date = models.DateTimeField(auto_now=True, null=True)

    # part from user
    email = models.EmailField(null=True, blank=True)
    msisdn = models.CharField(blank=True, null=True, max_length=14)

    # part by system
    token = models.CharField(max_length=64)
    passcode = models.CharField(max_length=25)
    valid_until = models.DateTimeField(blank=True, null=True, editable=False)
    valid_until_timestamp = models.IntegerField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    challenge = models.SlugField(
        choices=OTP_CHALLENGE,
        max_length=128, null=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z_][0-9a-zA-Z_]*$',
                message=_(
                    "Code can only contain the letters a-z, A-Z, digits, "
                    "and underscores, and can't start with a digit.")),
            non_python_keyword
        ]
    )

    objects = OTPFactoryQuerySet.as_manager()

    class Meta:
        abstract = True
        app_label = 'person'
        verbose_name = _(u"OTP Factory")
        verbose_name_plural = _(u"OTP Factories")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.passcode

    def clean(self):
        if not self.pk and not self.user:
            user_query = User.objects \
                .prefetch_related(Prefetch('account')) \
                .select_related('account')

            if self.email:
                try:
                    validate_email(self.email)
                except ValidationError as e:
                    raise ValidationError(_(e.message))

                # Registration each account has different email
                if self.challenge == REGISTER_VALIDATION:
                    user_query = user_query.filter(email=self.email, account__email_verified=True)
                    if user_query.exists():
                        raise ValidationError(_(u"Email `{email}` sudah terdaftar.".format(email=self.email)))

            # Reset password make sure account exist
            if self.challenge == PASSWORD_RECOVERY or self.challenge == CHANGE_EMAIL:
                user_query = user_query.filter(
                    Q(email=Case(When(email__isnull=False, then=Value(self.email))))
                    | Q(account__msisdn=Case(When(account__msisdn__isnull=False, then=Value(self.msisdn)))))

                if not user_query.exists():
                    raise ValidationError(_(u"Akun tidak ditemukan."))

            if self.challenge not in dict(OTP_CHALLENGE):
                raise ValidationError(
                    _(u"%s is not a valid choice." % self.get_challenge_display()))

    def validate(self):
        if self.is_used:
            raise ValidationError(_(u"Has used on %s" % (self.update_date)))

        if self.is_verified:
            raise ValidationError(_(u"Has verified on %s" % (self.update_date)))

        if self.is_expired:
            raise ValidationError(_(u"Has expired on %s" % (self.update_date)))

        if timezone.now() >= self.valid_until:
            self.is_expired = True
            self.save(update_fields=['is_expired'])
            raise ValidationError(_(u"OTP code expired on %s." % (self.valid_until)))

        # now real validation
        totp = pyotp.TOTP(self.token)
        passed = totp.verify(self.passcode, for_time=self.valid_until_timestamp)
        if not passed:
            raise ValidationError(_(u"OTP Code invalid."))

        # all passed and mark as verified!
        self.is_verified = True
        self.save(update_fields=['is_verified'])

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=['is_used'])

    def generate(self):
        # Set max validity date
        # Default 2 hours since created
        self.valid_until = timezone.now() + timezone.timedelta(hours=2)
        self.valid_until_timestamp = self.valid_until.replace(microsecond=0).timestamp()

        # generate OTP
        token = pyotp.random_base32()
        otp = pyotp.TOTP(token)
        passcode = otp.at(self.valid_until_timestamp)

        # save to database
        self.passcode = passcode
        self.token = token

    def save(self, *args, **kwargs):
        challenge = self.challenge

        # Set email from user email
        user_email = getattr(self.user, 'email', None)
        if user_email and challenge != CHANGE_EMAIL:
            self.email = user_email

        # generate OTP code
        self.generate()
        super().save(*args, **kwargs)
