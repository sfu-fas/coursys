from django.core.management.base import BaseCommand
from django.core.cache import cache

class Command(BaseCommand):
    help = "Called only as part of check_things. Doesn't do anything useful on its own."

    def handle(self, *args, **kwargs):
        res = cache.get('check_things_cache_test', -100)
        cache.set('check_things_cache_test', res + 1)







