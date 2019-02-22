# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0006_futureperson_email'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='futureperson',
            options={'verbose_name_plural': 'FuturePeople'},
        ),
        migrations.AddField(
            model_name='futureperson',
            name='hidden',
            field=models.BooleanField(default=False, editable=False),
        ),
    ]
