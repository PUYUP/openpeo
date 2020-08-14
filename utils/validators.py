import uuid
import keyword

from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.html import strip_tags, escape


IDENTIFIER_VALIDATOR = RegexValidator(
    regex=r'^[a-zA-Z_][a-zA-Z_]*$',
    message=_(u"Can only contain the letters a-z and underscores.")
)


def non_python_keyword(value):
    if keyword.iskeyword(value):
        raise ValidationError(
            _(u"This field is invalid as its value is forbidden.")
        )
    return value


def is_valid_uuid(uuid_to_test, version=4):
    """
    Check if uuid_to_test is a valid UUID.

    Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}

    Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.

    Examples
    --------
    >>> is_valid_uuid('c9bf9e57-1685-4c89-bafb-ff5af830be8a')
    True
    >>> is_valid_uuid('c9bf9e58')
    False
    """
    try:
        uuid_obj = uuid.UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def make_safe_string(data):
    # clear unsafe html string
    for key in data:
        string = data.get(key, None)
        if string and isinstance(string, str):
            string = escape(strip_tags(string))
            data[key] = string
    return data
