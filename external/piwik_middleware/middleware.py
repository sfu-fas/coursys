from .conf import settings
from importlib import import_module

# by default this is .tracking.PiwikTrackerLogic()
tracking_logic = import_module(settings.PIWIK_TRACKING_LOGIC).PiwikTrackerLogic()

class PiwikMiddleware(object):
    def process_response(self, request, response):
        """
        Record Piwik page view.
        """
        tracking_logic.track_page_view(request, response)
        return response