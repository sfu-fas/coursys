# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='location',
            field=models.CharField(max_length=150, null=True, blank=True),
        ),
    ]
