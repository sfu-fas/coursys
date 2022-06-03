import json

from django.core.management.base import BaseCommand
from django.db import connection
import time


INTERVAL = 10
QUERY = "SELECT label, name FROM coredata_unit WHERE slug='univ'"
EXPECTED = ('UNIV', 'Simon Fraser University')


def check_db():
    with connection.cursor() as cursor:
        start = time.time()
        try:
            cursor.execute(QUERY, [])
            row = cursor.fetchone()
            exception = ''
        except Exception as e:
            row = ()
            exception = str(e)
        end = time.time()

        data = {
            'start': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start)),
            'elapsed': end - start,
            'correct': row == EXPECTED,
            'exception': exception,
        }
        print(json.dumps(data), flush=True)


class Command(BaseCommand):
    def handle(self, *args, **options):
        while True:
            time.sleep(INTERVAL - time.time() % INTERVAL)
            check_db()
