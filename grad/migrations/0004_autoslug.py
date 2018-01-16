# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('grad', '0003_fix_choices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gradprogram',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'unit',), editable=False),
        ),
        migrations.AlterField(
            model_name='gradstudent',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='letter',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='lettertemplate',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', editable=False),
        ),
    ]
