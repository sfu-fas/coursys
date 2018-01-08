# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('grades', '0002_gradehistory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='slug',
            field=autoslug.fields.AutoSlugField(help_text=b'String that identifies this activity within the course offering', populate_from=b'autoslug', unique_with=(b'offering',), editable=False),
        ),
    ]
