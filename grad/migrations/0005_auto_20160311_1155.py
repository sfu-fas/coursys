# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grad', '0004_autoslug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supervisor',
            name='supervisor_type',
            field=models.CharField(max_length=3, choices=[(b'SEN', b'Senior Supervisor'), (b'COS', b'Co-senior Supervisor'), (b'COM', b'Supervisor'), (b'CHA', b'Defence Chair'), (b'EXT', b'External Examiner'), (b'SFU', b'SFU Examiner'), (b'POT', b'Potential Supervisor')]),
        ),
    ]
