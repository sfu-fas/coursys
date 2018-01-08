# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0002_entity_markup'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pageversion',
            name='page',
            field=models.ForeignKey(blank=True, to='pages.Page', null=True),
        ),
    ]
