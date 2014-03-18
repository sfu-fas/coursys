import cStringIO
import codecs
import csv

from django.http import HttpResponse

import unicodecsv


def make_csv_writer_response(filename, *args, **kwargs):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    return unicodecsv.writer(response), response
