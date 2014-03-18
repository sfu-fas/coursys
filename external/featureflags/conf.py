from django.conf import settings
from appconf import AppConf

class FlagsAppConf(AppConf):
    LOADER = 'featureflags.loaders.settings_loader'
    VIEW = 'featureflags.views.service_unavailable'
    DISABLED_TEMPLATE = '503.html'
    CACHE_TIMEOUT = 10

    DISABLE = set() # for settings_loader
    FILENAME = 'disabled_features.json' # for file_loader

    class Meta:
        prefix = 'featureflags'