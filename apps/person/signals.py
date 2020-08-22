import os

from django.db import transaction, IntegrityError
from django.db.models import Q, F, Case, When, Value
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from utils.generals import get_model
from apps.person.utils.constants import ROLE_DEFAULTS
from apps.person.utils.auth import set_roles

# Celery task
from apps.person.tasks import send_otp_email

Account = get_model('person', 'Account')
Profile = get_model('person', 'Profile')
Role = get_model('person', 'Role')


@transaction.atomic
def user_save_handler(sender, instance, created, **kwargs):
    if created:
        account = getattr(instance, 'account', None)
        if account is None:
            try:
                Account.objects.create(user=instance, email=instance.email,
                                       email_verified=True)
            except IntegrityError:
                pass

        profile = getattr(instance, 'profile', None)
        if profile is None:
            try:
                Profile.objects.create(user=instance)
            except IntegrityError:
                pass

        # Set roles if created by admin
        roles = getattr(instance, 'roles_value', None)
        if roles is None:
            # Set roles on register
            Role.objects.create(user=instance)

            # set default roles
            roles = list()
            for item in ROLE_DEFAULTS:
                roles.append(item[0])
        set_roles(user=instance, roles=roles)

    if not created:
        # create Account if not exist
        if not hasattr(instance, 'account'):
            Account.objects.create(user=instance, email=instance.email,
                                   email_verified=False)
        else:
            instance.account.email = instance.email
            instance.account.save()

        # create Profile if not exist
        if not hasattr(instance, 'profile'):
            Profile.objects.create(user=instance)


@transaction.atomic
def otpcode_save_handler(sender, instance, created, **kwargs):
    # create tasks
    # run only on resend and created
    if instance.is_used == False and instance.is_verified == False:
        if instance.email:
            data = {
                'email': getattr(instance, 'email', None),
                'passcode': getattr(instance, 'passcode', None)
            }
            send_otp_email.delay(data)

        # mark older OTP Code to expired
        oldest = instance.__class__.objects \
            .filter(
                Q(challenge=instance.challenge),
                Q(is_used=False), Q(is_expired=False),
                Q(email=Case(When(email__isnull=False, then=Value(instance.email))))
                | Q(msisdn=Case(When(msisdn__isnull=False, then=Value(instance.msisdn))))
            ).exclude(passcode=instance.passcode)

        if oldest.exists():
            oldest.update(is_expired=True)
