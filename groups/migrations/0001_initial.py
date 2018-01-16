# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('grades', '0001_initial'),
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Group name', max_length=30)),
                ('groupForSemester', models.BooleanField(default=True)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('svn_slug', autoslug.fields.AutoSlugField(max_length=17, null=True, editable=False)),
                ('courseoffering', models.ForeignKey(to='coredata.CourseOffering')),
                ('manager', models.ForeignKey(to='coredata.Member')),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('confirmed', models.BooleanField(default=False)),
                ('activity', models.ForeignKey(to='grades.Activity')),
                ('group', models.ForeignKey(to='groups.Group')),
                ('student', models.ForeignKey(to='coredata.Member')),
            ],
            options={
                'ordering': ['student__person', 'activity'],
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='groupmember',
            unique_together=set([('student', 'activity')]),
        ),
        migrations.AlterUniqueTogether(
            name='group',
            unique_together=set([('name', 'courseoffering'), ('svn_slug', 'courseoffering'), ('slug', 'courseoffering')]),
        ),
    ]
