# -*- coding: utf-8 -*-


from django.db import models, migrations
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0003_remove_computingaccount'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnyPerson',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='FuturePerson',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_name', models.CharField(max_length=32)),
                ('first_name', models.CharField(max_length=32)),
                ('middle_name', models.CharField(max_length=32, null=True, blank=True)),
                ('pref_first_name', models.CharField(max_length=32, null=True, blank=True)),
                ('title', models.CharField(max_length=4, null=True, blank=True)),
                ('config', courselib.json_fields.JSONField(default={})),
            ],
        ),
        migrations.CreateModel(
            name='RoleAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_name', models.CharField(max_length=32)),
                ('first_name', models.CharField(max_length=32)),
                ('middle_name', models.CharField(max_length=32, null=True, blank=True)),
                ('pref_first_name', models.CharField(max_length=32, null=True, blank=True)),
                ('title', models.CharField(max_length=4, null=True, blank=True)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('userid', models.CharField(null=True, max_length=8, blank=True, help_text=b'SFU Unix userid (i.e. part of SFU email address before the "@").', unique=True, verbose_name=b'User ID', db_index=True)),
            ],
        ),
        migrations.AddField(
            model_name='anyperson',
            name='future_person',
            field=models.ForeignKey(to='coredata.FuturePerson'),
        ),
        migrations.AddField(
            model_name='anyperson',
            name='person',
            field=models.ForeignKey(to='coredata.Person'),
        ),
        migrations.AddField(
            model_name='anyperson',
            name='role_account',
            field=models.ForeignKey(to='coredata.RoleAccount'),
        ),
    ]
