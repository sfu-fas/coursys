from django.core.management.base import BaseCommand
from django.core.cache import cache

from featureflags.conf import settings
from featureflags.flags import cache_key

class Command(BaseCommand):
    help = 'Temporarily disable the features given in settings.FEATUREFLAGS_PANIC_DISABLE.'

    def handle(self, *args, **kwargs):
        timeout = settings.FEATUREFLAGS_PANIC_TIMEOUT
        flags = settings.FEATUREFLAGS_PANIC_DISABLE

        if not flags:
            self.stdout.write(
                "You have not listed any disable-when-panicked features in settings.FEATUREFLAGS_PANIC_DISABLE. \n"
                "Nothing to disable here. Please continue to panic.")
            return

        cache.set(cache_key, flags, timeout)
        self.stdout.write("These features have been disabled for %s seconds:\n" % (timeout))
        for f in flags:
            self.stdout.write("  " + f)
        self.stdout.write("Best of luck. You may return to normal operation by calling 'manage.py unpanic'.\n")

