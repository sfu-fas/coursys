# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0007_position_any_person'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='degree1',
            field=models.CharField(default=b'', max_length=12),
        ),
        migrations.AddField(
            model_name='position',
            name='degree2',
            field=models.CharField(default=b'', max_length=12),
        ),
        migrations.AddField(
            model_name='position',
            name='degree3',
            field=models.CharField(default=b'', max_length=12),
        ),
        migrations.AddField(
            model_name='position',
            name='institution1',
            field=models.CharField(default=b'', max_length=25),
        ),
        migrations.AddField(
            model_name='position',
            name='institution2',
            field=models.CharField(default=b'', max_length=25),
        ),
        migrations.AddField(
            model_name='position',
            name='institution3',
            field=models.CharField(default=b'', max_length=25),
        ),
        migrations.AddField(
            model_name='position',
            name='location1',
            field=models.CharField(default=b'', max_length=23),
        ),
        migrations.AddField(
            model_name='position',
            name='location2',
            field=models.CharField(default=b'', max_length=23),
        ),
        migrations.AddField(
            model_name='position',
            name='location3',
            field=models.CharField(default=b'', max_length=23),
        ),
        migrations.AddField(
            model_name='position',
            name='year1',
            field=models.CharField(default=b'', max_length=5),
        ),
        migrations.AddField(
            model_name='position',
            name='year2',
            field=models.CharField(default=b'', max_length=5),
        ),
        migrations.AddField(
            model_name='position',
            name='year3',
            field=models.CharField(default=b'', max_length=5),
        ),
        migrations.AlterField(
            model_name='position',
            name='step',
            field=models.DecimalField(max_digits=3, decimal_places=1),
        ),
    ]
