# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0010_auto_20160119_1409'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='roleaccount',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='roleaccount',
            name='last_name',
        ),
        migrations.RemoveField(
            model_name='roleaccount',
            name='middle_name',
        ),
        migrations.RemoveField(
            model_name='roleaccount',
            name='pref_first_name',
        ),
        migrations.RemoveField(
            model_name='roleaccount',
            name='title',
        ),
        migrations.AddField(
            model_name='roleaccount',
            name='description',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='roleaccount',
            name='label',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='anyperson',
            name='future_person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='coredata.FuturePerson', null=True),
        ),
        migrations.AlterField(
            model_name='anyperson',
            name='person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='coredata.Person', null=True),
        ),
        migrations.AlterField(
            model_name='anyperson',
            name='role_account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='coredata.RoleAccount', null=True),
        ),
    ]
