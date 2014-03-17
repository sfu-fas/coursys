from django.conf import settings

def get_disabled_features():
    return settings.DISABLED_FEATURES