# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('discipline', '0002_django18'),
    ]

    operations = [
        migrations.AlterField(
            model_name='disciplinecasebase',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'offering',), editable=False),
        ),
        migrations.AlterField(
            model_name='disciplinegroup',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=(b'offering',), editable=False),
        ),
    ]
