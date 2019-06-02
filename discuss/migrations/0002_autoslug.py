# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('discuss', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discussionmessage',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=[b'topic'], editable=False),
        ),
        migrations.AlterField(
            model_name='discussiontopic',
            name='slug',
            field=autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique_with=[b'offering'], editable=False),
        ),
    ]
