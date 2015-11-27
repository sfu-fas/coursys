# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onlineforms', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fieldsubmissionfile',
            name='field_submission',
            field=models.OneToOneField(to='onlineforms.FieldSubmission'),
        ),
    ]
