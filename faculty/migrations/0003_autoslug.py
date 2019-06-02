# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0002_django18'),
    ]

    operations = [
        migrations.AlterField(
            model_name='careerevent',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'slug_string', unique_with=(b'person',), editable=False),
        ),
        migrations.AlterField(
            model_name='documentattachment',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'title', unique_with=(b'career_event',), editable=False),
        ),
        migrations.AlterField(
            model_name='grant',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'title', unique_with=(b'unit',), editable=False),
        ),
        migrations.AlterField(
            model_name='memo',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'career_event',), editable=False),
        ),
        migrations.AlterField(
            model_name='memotemplate',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
    ]
