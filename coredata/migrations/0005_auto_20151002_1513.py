# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0004_auto_20151002_1405'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anyperson',
            name='future_person',
            field=models.ForeignKey(to='coredata.FuturePerson', null=True),
        ),
        migrations.AlterField(
            model_name='anyperson',
            name='person',
            field=models.ForeignKey(to='coredata.Person', null=True),
        ),
        migrations.AlterField(
            model_name='anyperson',
            name='role_account',
            field=models.ForeignKey(to='coredata.RoleAccount', null=True),
        ),
    ]
