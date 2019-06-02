# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tacontracts', '0003_auto_20150402_1248'),
    ]

    operations = [
        migrations.AddField(
            model_name='tacontract',
            name='visa_verified',
            field=models.BooleanField(default=False, help_text=b"I have verified this TA's visa information"),
            preserve_default=True,
        ),
    ]
