# -*- coding: utf-8 -*-


from django.db import models, migrations
import faculty.models
import django.core.files.storage


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0011_auto_20151116_1456'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='teaching_semester_credits',
            field=models.DecimalField(null=True, max_digits=3, decimal_places=0, blank=True),
        ),
        migrations.AlterField(
            model_name='positiondocumentattachment',
            name='contents',
            field=models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, upload_to=faculty.models.position_attachment_upload_to),
        ),
    ]
