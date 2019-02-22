# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('discipline', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='disciplinecasechairnonstudent',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='disciplinecasechairnonstudent',
            name='emplid',
            field=models.PositiveIntegerField(help_text=b'SFU student number, if known', null=True, verbose_name=b'Student Number', blank=True),
        ),
        migrations.AlterField(
            model_name='disciplinecaseinstrnonstudent',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='disciplinecaseinstrnonstudent',
            name='emplid',
            field=models.PositiveIntegerField(help_text=b'SFU student number, if known', null=True, verbose_name=b'Student Number', blank=True),
        ),
    ]
