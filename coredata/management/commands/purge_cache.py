from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = "Purge everything in the Django cache."

    def handle(self, *args, **options):
        cache.clear()
        