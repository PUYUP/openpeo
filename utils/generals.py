import uuid
import json
import random
import string
import importlib

from django.apps import apps
from django.apps.config import MODELS_MODULE_NAME
from django.core.exceptions import AppRegistryNotReady
from django.utils.functional import Promise
from django.utils.encoding import force_text
from django.core.serializers.json import DjangoJSONEncoder

from rest_framework import renderers


class LazyEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_text(obj)
        return super(LazyEncoder, self).default(obj)


class JSONExtendRenderer(renderers.BaseRenderer):
    media_type = 'application/json'
    format = 'json'

    def render(self, data, media_type=None, renderer_context=None):
        return data.encode(self.charset)


def is_model_registered(app_label, model_name):
    """
    Checks whether a given model is registered. This is used to only
    register Oscar models if they aren't overridden by a forked app.
    """
    try:
        apps.get_registered_model(app_label, model_name)
    except LookupError:
        return False
    else:
        return True


def get_model(app_label, model_name):
    """
    Fetches a Django model using the app registry.

    This doesn't require that an app with the given app label exists,
    which makes it safe to call when the registry is being populated.
    All other methods to access models might raise an exception about the
    registry not being ready yet.
    Raises LookupError if model isn't found.
    """
    try:
        return apps.get_model(app_label, model_name)
    except AppRegistryNotReady:
        if apps.apps_ready and not apps.models_ready:
            # If this function is called while `apps.populate()` is
            # loading models, ensure that the module that defines the
            # target model has been imported and try looking the model up
            # in the app registry. This effectively emulates
            # `from path.to.app.models import Model` where we use
            # `Model = get_model('app', 'Model')` instead.
            app_config = apps.get_app_config(app_label)

            # `app_config.import_models()` cannot be used here because it
            # would interfere with `apps.populate()`.
            importlib.import_module('%s.%s' % (app_config.name, MODELS_MODULE_NAME))

            # In order to account for case-insensitivity of model_name,
            # look up the model through a private API of the app registry.
            return apps.get_registered_model(app_label, model_name)
        else:
            # This must be a different case (e.g. the model really doesn't
            # exist). We just re-raise the exception.
            raise


def random_string(length=6):
    code = uuid.uuid4().hex
    code = code.upper()[0:length]
    return code


def create_unique_id():
    return ''.join(random.choices(string.digits, k=8))


def choices_to_json(choices):
    to_dict = dict(choices)
    return json.dumps(to_dict, cls=LazyEncoder)
