# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grad', '0006_lettertemplate_config'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gradstudent',
            name='passport_issued_by',
            field=models.CharField(help_text=b'I.e. US, China', max_length=30, blank=True),
        ),
    ]
