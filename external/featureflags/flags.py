from django.utils import importlib
from django.core.urlresolvers import get_callable
from django.core.cache import cache
from featureflags.conf import settings

cache_timeout = settings.FEATUREFLAGS_CACHE_TIMEOUT
def _cache_key():
    site = getattr(settings, 'SITE_ID', '')
    return 'featureflags-%s-flags' % (site)

cache_key = _cache_key()

def get_loader():
    module = settings.FEATUREFLAGS_LOADER
    return importlib.import_module(module)

def get_disabled_view():
    module = settings.FEATUREFLAGS_DISABLED_VIEW
    return get_callable(module)


def disabled_features():
    """
    Get the current set of disabled features: from the Django cache if possible, or from the loader if not.
    """
    if cache_timeout:
        # check the cache and return it if we find it
        flags = cache.get(cache_key)
        if flags is not None:
            return flags

    # not in the cache: have the loader find it
    loader = get_loader()
    flags = loader.get_disabled_features()
    if cache_timeout:
        cache.set(cache_key, flags, cache_timeout)

    return flags


def feature_disabled(feature):
    return feature in disabled_features()

def feature_enabled(feature):
    return not feature_disabled(feature)


def uses_feature(feature):
    """
    Decorator to allow disabling views temporarily.
    """
    def decorator(function): # the decorator with 'feature' argument closed
        def view(*args, **kwargs): # the actual view returned by the decorator
            if feature_disabled(feature):
                return get_disabled_view()(*args, **kwargs)
            else:
                return function(*args, **kwargs)
        return view

    return decorator

