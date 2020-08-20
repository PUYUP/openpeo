from django.utils.translation import ugettext_lazy as _


REGISTERED = 'registered'
SELLER = 'seller'
BUYER = 'buyer'
ROLE_IDENTIFIERS = (
    (REGISTERED, _(u"Registered")),
    (SELLER, _(u"Seller")),
    (BUYER, _(u"Buyer")),
)

ROLE_DEFAULTS = (
    (REGISTERED, _(u"Registered")),
    (SELLER, _(u"Client")),
)


OTP_SESSION_FIELDS = ['uuid', 'token', 'challenge', 'msisdn', 'email',
                      'send_to_message']
EMAIL_VALIDATION = 'email_validation'
MSISDN_VALIDATION = 'msisdn_validation'
REGISTER_VALIDATION = 'register_validation'
PASSWORD_RECOVERY = 'password_recovery'
CHANGE_MSISDN = 'change_msisdn'
CHANGE_MSISDN_VALIDATION = 'change_msisdn_validation'
CHANGE_EMAIL = 'change_email'
CHANGE_EMAIL_VALIDATION = 'change_email_validation'
CHANGE_USERNAME = 'change_username'
CHANGE_PASSWORD = 'change_password'
OTP_CHALLENGE = (
    (EMAIL_VALIDATION, _(u"Email Validation")),
    (MSISDN_VALIDATION, _(u"MSISDN Validation")),
    (REGISTER_VALIDATION, _(u"Register Validation")),
    (PASSWORD_RECOVERY, _(u"Password Recovery")),
    (CHANGE_MSISDN, _(u"Change MSISDN")),
    (CHANGE_MSISDN_VALIDATION, _(u"Change MSISDN Validation")),
    (CHANGE_EMAIL, _(u"Change Email")),
    (CHANGE_EMAIL_VALIDATION, _(u"Change Email Validation")),
    (CHANGE_USERNAME, _(u"Change Username")),
    (CHANGE_PASSWORD, _(u"Change Password")),
)


UNDEFINED = 'unknown'
MALE = 'male'
FEMALE = 'female'
GENDER_CHOICES = (
    (UNDEFINED, _(u"Unknown")),
    (MALE, _(u"Male")),
    (FEMALE, _(u"Female")),
)


JAN = '1'
FEB = '2'
MAR = '3'
APR = '4'
MAY = '5'
JUN = '6'
JUL = '7'
AUG = '8'
SEP = '9'
OCT = '10'
NOV = '11'
DEC = '12'

MONTH_CHOICES = (
    (JAN, _(u"January")),
    (FEB, _(u"February")),
    (MAR, _(u"March")),
    (APR, _(u"April")),
    (MAY, _(u"May")),
    (JUN, _(u"June")),
    (JUL, _(u"July")),
    (AUG, _(u"August")),
    (SEP, _(u"September")),
    (OCT, _(u"October")),
    (NOV, _(u"November")),
    (DEC, _(u"December")),
)

