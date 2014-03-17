from django.conf import settings
from django.utils import importlib
DEFAULT_LOADER = 'featureflags.loaders.settings_loader'
DEFAULT_VIEW = 'featureflags.views.service_unavailable'

def get_loader():
    module = getattr(settings, 'FEATUREFLAGS_LOADER', DEFAULT_LOADER)
    return importlib.import_module(module)

from django.core.urlresolvers import get_callable
def get_disabled_view():
    module = getattr(settings, 'FEATUREFLAGS_DISABLED_VIEW', DEFAULT_VIEW)
    return get_callable(module)


def disabled_features():
    loader = get_loader()
    return loader.get_disabled_features()

#def _return_unavailable(request, *args, **kwargs):
#    return HttpError(request, status=503, title="Service Unavailable", error="This feature has been temporarily disabled due to server maintenance or load.", errormsg=None, simple=False)


def feature_disabled(feature):
    return feature in disabled_features()

def feature_enabled(feature):
    return not feature_disabled(feature)


def uses_feature(feature):
    """
    Decorator to allow disabling views temporarily.
    """
    def real_decorator(function):
        if feature_disabled(feature):
            return get_disabled_view()
        else:
            return function
    return real_decorator

