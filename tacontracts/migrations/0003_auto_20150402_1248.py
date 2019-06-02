# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('tacontracts', '0002_tacategory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tacategory',
            name='created',
            field=models.DateTimeField(default=datetime.datetime.now, editable=False),
            preserve_default=True,
        ),
    ]
