# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('advisornotes', '0002_advisornote_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='nonstudent',
            name='email_address',
            field=models.EmailField(help_text=b'Needed only if you want to copy the student on notes', max_length=75, null=True, blank=True),
            preserve_default=True,
        ),
    ]
