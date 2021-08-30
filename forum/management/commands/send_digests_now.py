from django.core.management.base import BaseCommand
from forum.tasks import send_digests


class Command(BaseCommand):
    help = 'Send forum digest emails now.'

    def handle(self, *args, **options):
        send_digests.apply(kwargs={'immediate': True})
