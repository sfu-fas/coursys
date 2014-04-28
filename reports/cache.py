from django.conf import settings
import shutil
import os

def clear_cache():
    """ Remove the contents of /tmp/report_cache """
    if settings.REPORT_CACHE_CLEAR: 
        try:
            shutil.rmtree(settings.REPORT_CACHE_LOCATION)
        except OSError:
            return
