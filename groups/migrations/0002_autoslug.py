# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'courseoffering',), editable=False),
        ),
        migrations.AlterField(
            model_name='group',
            name='svn_slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'slug', unique_with=(b'courseoffering',), null=True, editable=False),
        ),
    ]
