# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='courseoffering',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
        migrations.AlterField(
            model_name='unit',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False),
        ),
    ]
