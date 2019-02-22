# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('tacontracts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tacategory',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2014, 12, 21, 15, 43, 21, 814524), editable=False),
            preserve_default=True,
        ),
    ]
