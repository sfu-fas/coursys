from django.core.management.base import BaseCommand
from django.core.cache import cache

from featureflags.conf import settings
from featureflags.flags import cache_key

class Command(BaseCommand):
    help = 'Return to featureflags to normal operation.'

    def handle(self, *args, **kwargs):
        cache.delete(cache_key)

