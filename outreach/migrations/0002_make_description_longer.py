# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outreach', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='outreachevent',
            name='description',
            field=models.CharField(max_length=800, null=True, blank=True),
        ),
    ]
