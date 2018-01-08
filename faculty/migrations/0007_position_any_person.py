# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0004_auto_20151002_1405'),
        ('faculty', '0006_auto_20150729_1017'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='any_person',
            field=models.ForeignKey(blank=True, to='coredata.AnyPerson', null=True),
        ),
    ]
