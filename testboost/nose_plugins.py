# hee hee
# http://pypede.wordpress.com/2012/06/17/disable-south-debug-logging-when-testing-apps-with-nose-in-django/

from nose.plugins import Plugin
import logging

class SilenceSouth(Plugin):
    south_logging_level = logging.ERROR

    def configure(self, options, conf):
        super(SilenceSouth, self).configure(options, conf)
        logging.getLogger('south').setLevel(self.south_logging_level)
