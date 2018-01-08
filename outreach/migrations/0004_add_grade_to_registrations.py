# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outreach', '0003_add_previously_attended_field_to_registration'),
    ]

    operations = [
        migrations.AddField(
            model_name='outreacheventregistration',
            name='grade',
            field=models.PositiveSmallIntegerField(default=1, verbose_name=b'Participant Grade'),
            preserve_default=False,
        ),
    ]
