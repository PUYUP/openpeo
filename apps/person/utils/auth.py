import itertools

from django.db.models import Prefetch
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import _unicode_ci_compare
from django.contrib.auth.validators import UnicodeUsernameValidator

from utils.generals import get_model
from apps.person.utils.constants import OTP_SESSION_FIELDS

validate_username = UnicodeUsernameValidator()

User = get_model('person', 'User')


class CurrentUserDefault:
    """Return current logged-in user"""
    def set_context(self, serializer_field):
        user = serializer_field.context['request'].user
        self.user = user

    def __call__(self):
        return self.user

    def __repr__(self):
        return '%s()' % self.__class__.__name__


class LoginBackend(ModelBackend):
    """Login w/h username or email"""
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        try:
            # user = User._default_manager.get_by_natural_key(username)
            # You can customise what the given username is checked against, here I compare to both username and email fields of the User model
            user = User.objects \
                .filter(
                    Q(username__iexact=username)
                    | Q(email__iexact=username)
                    | Q(account__msisdn=username)
                    & Q(account__msisdn_verified=True))
        except User.DoesNotExist:
            # Run the default password tokener once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            User().set_password(password)
        else:
            try:
                user = user.get(Q(username__iexact=username) | Q(email__iexact=username)
                                | Q(account__msisdn=username)
                                & Q(account__msisdn_verified=True))
            except User.DoesNotExist:
                return None

            if user and user.check_password(password) and self.user_can_authenticate(user):
                return user
        return super().authenticate(request, username, password, **kwargs)


class GuestRequiredMixin:
    """Verify that the current user guest."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('home'))
        return super().dispatch(request, *args, **kwargs)


def get_users_by_email(email):
    """Given an email, return matching user(s) who should receive a reset.
    This allows subclasses to more easily customize the default policies
    that prevent inactive users and users with unusable passwords from
    resetting their password.
    """
    email_field_name = User.get_email_field_name()
    active_users = User._default_manager.filter(**{
        '%s__iexact' % email_field_name: email,
        'is_active': True,
    })
    return (
        u for u in active_users
        if u.has_usable_password() and
        _unicode_ci_compare(email, getattr(u, email_field_name))
    )


def clear_otp_session(request, interact):
    # clear otp session
    for key in OTP_SESSION_FIELDS:
        try:
            del request.session['otp_%s_%s' % (interact, key)]
        except KeyError:
            pass


def set_roles(user=None, roles=list()):
    """
    :user is user object
    :roles is list of identifier for role, egg: ['registered', 'seller']
    """
    RoleCapabilities = get_model('person', 'RoleCapabilities')

    roles_created = list()
    identifiers_initial = list(user.roles.values_list('identifier', flat=True))
    identifiers_new = list(set(roles) - set(identifiers_initial))

    for identifier in identifiers_new:
        role_obj = user.roles.model(user=user, identifier=identifier)
        roles_created.append(role_obj)

    if roles_created:
        user.roles.model.objects.bulk_create(roles_created)

    capabilities_objs = RoleCapabilities.objects \
        .prefetch_related(Prefetch('permissions')) \
        .filter(identifier__in=user.roles.all().values('identifier'))
    permission_objs = [list(item.permissions.all()) for item in capabilities_objs]
    permission_objs_unique = list(set(itertools.chain.from_iterable(permission_objs)))
    user.user_permissions.add(*permission_objs_unique)


def update_roles(user=None, roles=list()):
    """
    :user is user object
    :roles is list of identifier for role, egg: ['registered', 'seller']
    """
    RoleCapabilities = get_model('person', 'RoleCapabilities')

    permissions_removed = list()
    permissions_add = list()
    permissions_current = user.user_permissions.all()
    capabilities = RoleCapabilities.objects \
        .prefetch_related(Prefetch('permissions'))

    # REMOVE ROLES
    roles_removed = user.roles.exclude(identifier__in=roles)
    if roles_removed.exists():
        capabilities = capabilities.filter(identifier__in=roles_removed.values('identifier'))
        permissions = [list(item.permissions.all()) for item in capabilities]
        permissions_removed = list(set(itertools.chain.from_iterable(permissions)))
        roles_removed.delete()

    # ADD ROLES
    if roles:
        roles_created = list()
        identifiers_initial = list(user.roles.values_list('identifier', flat=True))
        identifiers_new = list(set(roles) ^ set(identifiers_initial))

        for identifier in identifiers_new:
            role_obj = user.roles.model(user=user, identifier=identifier)
            roles_created.append(role_obj)

        if roles_created:
            user.roles.model.objects.bulk_create(roles_created)

        capabilities = capabilities.filter(identifier__in=user.roles.all().values('identifier'))
        permissions = [list(item.permissions.all()) for item in capabilities]
        permissions_add = list(set(itertools.chain.from_iterable(permissions)))

    # Compare current with new permissions
    # If has different assign that to user
    if permissions_current:
        add_diff = list(set(permissions_add) & set(permissions_current))
        if add_diff:
            add_diff = list(set(permissions_add) ^ set(add_diff))
    else:
        add_diff = list(set(permissions_add))

    if add_diff and permissions_add:
        user.user_permissions.add(*list(add_diff))

    # Compare current with old permissions
    # If has different remove that
    removed_diff = list(set(permissions_add) ^ set(permissions_removed))
    if removed_diff and permissions_removed:
        diff = set(removed_diff) & set(permissions_removed)
        user.user_permissions.remove(*list(diff))
