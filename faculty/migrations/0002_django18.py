# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facultymemberinfo',
            name='person',
            field=models.OneToOneField(related_name='+', to='coredata.Person'),
        ),
        migrations.AlterField(
            model_name='grant',
            name='owners',
            field=models.ManyToManyField(help_text=b'Who owns/controls this grant?', to='coredata.Person', through='faculty.GrantOwner'),
        ),
    ]
