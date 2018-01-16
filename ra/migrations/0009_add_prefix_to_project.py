# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ra', '0008_add_program_to_paf'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='project_prefix',
            field=models.CharField(help_text=b"If the project number has a prefix of 'R', 'X', etc, add it here", max_length=1, null=True, verbose_name=b'Prefix', blank=True),
        ),
    ]
