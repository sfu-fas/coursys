# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0012_auto_20151210_1357'),
    ]

    operations = [
        migrations.AlterField(
            model_name='position',
            name='any_person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='coredata.AnyPerson', null=True),
        ),
    ]
