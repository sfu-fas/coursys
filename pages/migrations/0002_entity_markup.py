# -*- coding: utf-8 -*-
"""
Replace any entities in all PageVersions with an escaped version (so it displays the same after pages.Page behaviour
change)
"""



from django.db import models, migrations

from courselib.markup import HTMLEntity
import re

regex = re.compile(HTMLEntity().re_string())

def escape_entity(txt):
    chars = list(txt)
    changes = 0
    for m in regex.finditer(txt):
        assert chars[m.start()] == '&'
        chars[m.start()] = '&amp;'
        changes += 1

    return ''.join(chars), changes

def escape_page_entities(apps, schema_editor):
    # I know I'm not supposed to import like this, but signals that are active need the real class...
    from pages.models import PageVersion
    for pv in PageVersion.objects.all():
        if pv.wikitext:
            pv.wikitext, changes = escape_entity(pv.wikitext)
        elif pv.diff:
            pv.diff, changes = escape_entity(pv.diff)
        else:
            changes = 0

        if changes > 0:
            pv.save()

class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0001_initial'),
    ]

    operations = [
        #migrations.RunPython(escape_page_entities),
    ]
