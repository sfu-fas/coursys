import re
from django.db import migrations, transaction

absolute_prefix = '/data/submitted_files/'
abs_re = re.compile(r'^' + re.escape(absolute_prefix))


# Some code caused absolute paths to end up in the database for PageVersion.file_attachment. They should be relative
# paths. This does some surgery to strip the absolute prefix.
def fix_paths(apps, schema_editor):
    PageVersion = apps.get_model('pages', 'PageVersion')
    abs_paths = PageVersion.objects.filter(file_attachment__startswith=absolute_prefix)
    with transaction.atomic():
        for v in abs_paths:
            path = v.file_attachment.name
            newpath = abs_re.sub('', path)
            v.file_attachment.name = newpath
            v.save()


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0006_on_delete'),
    ]

    operations = [
        migrations.RunPython(fix_paths),
    ]
