# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0005_auto_20151002_1513'),
    ]

    operations = [
        migrations.AddField(
            model_name='futureperson',
            name='email',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
    ]
