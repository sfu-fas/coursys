# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grades', '0003_autoslug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gradehistory',
            name='comment',
            field=models.TextField(max_length=5000, null=True),
        ),
        migrations.AlterField(
            model_name='lettergrade',
            name='comment',
            field=models.TextField(max_length=5000, null=True),
        ),
        migrations.AlterField(
            model_name='numericgrade',
            name='comment',
            field=models.TextField(max_length=5000, null=True),
        ),
    ]
