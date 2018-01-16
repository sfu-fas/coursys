# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0008_remove_futureperson_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anyperson',
            name='future_person',
            field=models.ForeignKey(blank=True, to='coredata.FuturePerson', null=True),
        ),
        migrations.AlterField(
            model_name='anyperson',
            name='person',
            field=models.ForeignKey(blank=True, to='coredata.Person', null=True),
        ),
        migrations.AlterField(
            model_name='anyperson',
            name='role_account',
            field=models.ForeignKey(blank=True, to='coredata.RoleAccount', null=True),
        ),
    ]
