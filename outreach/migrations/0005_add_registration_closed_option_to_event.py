# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outreach', '0004_add_grade_to_registrations'),
    ]

    operations = [
        migrations.AddField(
            model_name='outreachevent',
            name='closed',
            field=models.BooleanField(default=False, help_text=b'If this box is checked, people will not be able to register for this event even if it is still current.', verbose_name=b'Close Registration'),
        ),
    ]
