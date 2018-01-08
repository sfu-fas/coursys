# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0002_autoslug'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ComputingAccount',
        ),
        migrations.AlterField(
            model_name='combinedoffering',
            name='offerings',
            field=models.ManyToManyField(to='coredata.CourseOffering'),
        ),
    ]
