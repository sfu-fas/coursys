# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ra', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='raappointment',
            name='visa_verified',
            field=models.BooleanField(default=False, help_text=b"I have verified this RA's visa information"),
            preserve_default=True,
        ),
    ]
