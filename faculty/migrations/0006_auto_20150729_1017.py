# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0005_remove_position_teaching_load'),
    ]

    operations = [
        migrations.AlterField(
            model_name='position',
            name='unit',
            field=models.ForeignKey(to='coredata.Unit'),
        ),
    ]
