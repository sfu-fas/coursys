# -*- coding: utf-8 -*-


from django.db import migrations, models
import django.core.files.storage
import ta.models


class Migration(migrations.Migration):

    dependencies = [
        ('ta', '0004_auto_20151216_0908'),
    ]

    operations = [
        migrations.AddField(
            model_name='taapplication',
            name='resume',
            field=models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), upload_to=ta.models._resume_upload_to, max_length=500, blank=True, help_text=b'Please attach your Curriculum Vitae (CV).', null=True, verbose_name=b'Curriculum Vitae (CV)'),
        ),
        migrations.AddField(
            model_name='taapplication',
            name='resume_mediatype',
            field=models.CharField(max_length=200, null=True, editable=False, blank=True),
        ),
        migrations.AddField(
            model_name='taapplication',
            name='transcript',
            field=models.FileField(upload_to=ta.models._transcript_upload_to, storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, blank=True, help_text=b'Please attach your unofficial transcript.', null=True),
        ),
        migrations.AddField(
            model_name='taapplication',
            name='transcript_mediatype',
            field=models.CharField(max_length=200, null=True, editable=False, blank=True),
        ),
    ]
