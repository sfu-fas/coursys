from django.core.management.base import BaseCommand
from django.core.cache import cache
from optparse import make_option

from coredata import panel

class Command(BaseCommand):
    help = 'Check the status of the various things we rely on in deployment.'

    def add_arguments(self, parser):
        parser.add_argument('--cache_subcall',
                            action='store_true',
                            dest='cache_subcall',
                            default=False,
                            help="Called only as part of check_things. Doesn't do anything useful on its own.")
        parser.add_argument('--email',
                            dest='email',
                            default='',
                            help="Email this address to make sure it's sent.")


    def _report(self, title, reports):
        if reports:
            self.stdout.write('\n%s:\n' % (title))
        for criteria, message in reports:
            self.stdout.write('  %s: %s' % (criteria, message))

    def handle(self, *args, **options):
        if options['cache_subcall']:
            # add one to the cached value, so the main process can tell we see/update the same cache
            res = cache.get('check_things_cache_test', -100)
            cache.set('check_things_cache_test', res + 1)
            return

        info = panel.settings_info()
        passed, failed = panel.deploy_checks()
        unknown = []

        # email sending
        if options['email']:
            email = options['email']
            success, result = panel.send_test_email(email)
            if success:
                unknown.append(('Email sending', result))
            else:
                failed.append(('Email sending', result))
        else:
            unknown.append(('Email sending', "provide an --email argument to test."))

        # report results
        self._report('For information', info)
        self._report('These checks passed', passed)
        self._report('These checks failed', failed)
        self._report('Status unknown', unknown)
        self.stdout.write('\n')


