# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0014_auto_20160623_1509'),
        ('visas', '0005_auto_20151127_1128'),
    ]

    operations = [
        migrations.AddField(
            model_name='visa',
            name='unit',
            field=models.ForeignKey(default=34, to='coredata.Unit'),
            preserve_default=False,
        ),
    ]
