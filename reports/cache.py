from django.conf import settings
import shutil
import os

def cache_location():
    if not os.path.exists(settings.REPORT_CACHE_LOCATION):
        os.makedirs(settings.REPORT_CACHE_LOCATION)
    return settings.REPORT_CACHE_LOCATION

def clear_cache():
    """ Remove the contents of /tmp/report_cache """
    if settings.REPORT_CACHE_CLEAR: 
        try:
            shutil.rmtree(settings.REPORT_CACHE_LOCATION)
        except OSError:
            return
