from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q, Prefetch

from utils.generals import get_model
from apps.person.forms import UserChangeFormExtend, UserCreationFormExtend
from apps.person.utils.constants import ROLE_IDENTIFIERS

User = get_model('person', 'User')
Profile = get_model('person', 'Profile')
Account = get_model('person', 'Account')
Role = get_model('person', 'Role')
RoleCapabilities = get_model('person', 'RoleCapabilities')
OTPFactory = get_model('person', 'OTPFactory')
Permission = get_model('auth', 'Permission')


try:
    _ROLE_LENGTH = len(ROLE_IDENTIFIERS)
except NameError:
    _ROLE_LENGTH = 0


class ProfileInline(admin.StackedInline):
    model = Profile


class AccountInline(admin.StackedInline):
    model = Account
    readonly_fields = ('email',)


class RoleCapabilitiesExtend(admin.ModelAdmin):
    model = RoleCapabilities
    filter_horizontal = ('permissions',)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'permissions':
            kwargs['queryset'] = Permission.objects.prefetch_related(Prefetch('content_type')) \
                .select_related('content_type')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class UserExtend(UserAdmin):
    _INLINE_SET = [ProfileInline, AccountInline]

    form = UserChangeFormExtend
    add_form = UserCreationFormExtend
    inlines = _INLINE_SET
    list_display = ('username', 'first_name', 'email', 'msisdn', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password', 'email',)}),
        (_(u"Personal info"), {'fields': ('first_name', 'last_name',)}),
        (_(u"Permissions"), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser',),
        }),
        (_(u"Important dates"), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password1', 'password2', 'role',)
        }),
    )

    def msisdn(self, obj):
        return obj.account.msisdn
    msisdn.short_description = _(u"MSISDN")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        queryset = qs \
            .prefetch_related(Prefetch('account'), Prefetch('profile')) \
            .select_related('account', 'profile')
        return queryset


class OTPFactoryExtend(admin.ModelAdmin):
    model = OTPFactory
    list_display = ('email', 'msisdn', 'passcode', 'challenge', 'is_verified',
                    'is_used', 'is_expired', 'token',)
    list_display_links = ('email', 'msisdn',)
    readonly_fields = ('passcode', 'token', 'valid_until', 'valid_until_timestamp',)

    def get_readonly_fields(self, request, obj=None):
        # Disallow edit
        if obj:
            return list(set(
                [field.name for field in self.opts.local_fields] +
                [field.name for field in self.opts.local_many_to_many]))
        return super().get_readonly_fields(request, obj)

    def __init__(self,*args,**kwargs):
        super().__init__(*args, **kwargs)


admin.site.register(User, UserExtend)
admin.site.register(RoleCapabilities, RoleCapabilitiesExtend)
admin.site.register(OTPFactory, OTPFactoryExtend)
