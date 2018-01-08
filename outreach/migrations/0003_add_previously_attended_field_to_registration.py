# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outreach', '0002_make_description_longer'),
    ]

    operations = [
        migrations.AddField(
            model_name='outreacheventregistration',
            name='previously_attended',
            field=models.BooleanField(default=False, help_text=b'Check here if you have attended this event in the past', verbose_name=b'I have previously attended this event'),
        ),
    ]
