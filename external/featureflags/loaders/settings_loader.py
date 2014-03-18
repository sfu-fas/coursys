from django.conf import settings

def get_disabled_features():
    """
    Load the disabled features from the settings file
    """
    return settings.FEATUREFLAGS_DISABLE