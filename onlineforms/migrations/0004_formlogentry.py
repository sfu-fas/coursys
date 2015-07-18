# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0003_remove_computingaccount'),
        ('onlineforms', '0003_autoslug'),
    ]

    operations = [
        migrations.CreateModel(
            name='FormLogEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('category', models.CharField(max_length=4, choices=[(b'AUTO', b'Automatic change by system'), (b'MAIL', b'Email notification sent'), (b'', b''), (b'', b''), (b'', b'')])),
                ('description', models.CharField(help_text=b'Description of the action/change', max_length=255)),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('form_submission', models.ForeignKey(to='onlineforms.FormSubmission')),
                ('sheet_submission', models.ForeignKey(to='onlineforms.SheetSubmission', null=True)),
                ('user', models.ForeignKey(to='coredata.Person', help_text=b'User who took the action/made the change', null=True)),
            ],
        ),
    ]
