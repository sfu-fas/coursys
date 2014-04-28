from django.conf import settings
import json

def get_disabled_features():
    """
    Load the disabled features from a JSON file.
    """
    fh = open(settings.FEATUREFLAGS_FILENAME, 'rb')
    flags = json.load(fh, encoding='utf-8')
    return set(flags)