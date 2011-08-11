# from http://djangosnippets.org/snippets/2211/

from django.test.simple import DjangoTestSuiteRunner #@UnresolvedImport
import logging
from django.conf import settings
EXCLUDED_APPS = getattr(settings, 'TEST_EXCLUDE', [])

class AdvancedTestSuiteRunner(DjangoTestSuiteRunner):
    def __init__(self, *args, **kwargs):
        from django.conf import settings
        settings.TESTING = True
        south_log = logging.getLogger("south")
        south_log.setLevel(logging.WARNING)
        super(AdvancedTestSuiteRunner, self).__init__(*args, **kwargs)
    
    def build_suite(self, *args, **kwargs):
        suite = super(AdvancedTestSuiteRunner, self).build_suite(*args, **kwargs)
        if not args[0] and not getattr(settings, 'RUN_ALL_TESTS', False):
            tests = []
            for case in suite:
                pkg = case.__class__.__module__.split('.')[0]
                if pkg not in EXCLUDED_APPS:
                    tests.append(case)
            suite._tests = tests 
        return suite
    
