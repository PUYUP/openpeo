from .auth import *
from .account import *
from .role import *
from .otp import *

# PROJECT UTILS
from utils.generals import is_model_registered

__all__ = list()

# https://docs.djangoproject.com/en/3.1/topics/auth/customizing/#auth-custom-user
if not is_model_registered('person', 'User'):
    class User(User):
        class Meta(User.Meta):
            db_table = 'person_user'

    __all__.append('User')


# 0
if not is_model_registered('person', 'Profile'):
    class Profile(AbstractProfile):
        class Meta(AbstractProfile.Meta):
            db_table = 'person_profile'

    __all__.append('Profile')


# 1
if not is_model_registered('person', 'Account'):
    class Account(AbstractAccount):
        class Meta(AbstractAccount.Meta):
            db_table = 'person_account'

    __all__.append('Account')


# 2
if not is_model_registered('person', 'Role'):
    class Role(AbstractRole):
        class Meta(AbstractRole.Meta):
            db_table = 'person_role'

    __all__.append('Role')


# 3
if not is_model_registered('person', 'RoleCapabilities'):
    class RoleCapabilities(AbstractRoleCapabilities):
        class Meta(AbstractRoleCapabilities.Meta):
            db_table = 'person_role_capabilities'

    __all__.append('RoleCapabilities')


# 4
if not is_model_registered('person', 'OTPFactory'):
    class OTPFactory(AbstractOTPFactory):
        class Meta(AbstractOTPFactory.Meta):
            db_table = 'person_otp_factory'

    __all__.append('OTPFactory')
