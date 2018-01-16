# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import datetime
import django.core.files.storage
import advisornotes.models
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdvisorNote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField(help_text=b'Note about a student', verbose_name=b'Contents')),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('file_attachment', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, null=True, upload_to=advisornotes.models.attachment_upload_to, blank=True)),
                ('file_mediatype', models.CharField(max_length=200, null=True, editable=False, blank=True)),
                ('hidden', models.BooleanField(default=False, db_index=True)),
                ('emailed', models.BooleanField(default=False)),
                ('advisor', models.ForeignKey(related_name='advisor', editable=False, to='coredata.Person', help_text=b'The advisor that created the note')),
            ],
            options={
                'ordering': ['student', 'created_at'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AdvisorVisit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('advisor', models.ForeignKey(related_name='+', editable=False, to='coredata.Person', help_text=b'The advisor that created the note')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Artifact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'The name of the artifact', max_length=140)),
                ('category', models.CharField(max_length=3, choices=[(b'INS', b'Institution'), (b'PRO', b'Program'), (b'OTH', b'Other')])),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('unit', models.ForeignKey(help_text=b'The academic unit that owns this artifact', to='coredata.Unit')),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ArtifactNote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('important', models.BooleanField(default=False)),
                ('category', models.CharField(max_length=3, choices=[(b'EXC', b'Exceptions'), (b'WAI', b'Waivers'), (b'REQ', b'Requirements'), (b'TRA', b'Transfers'), (b'MIS', b'Miscellaneous')])),
                ('text', models.TextField(help_text=b'Note about a student', verbose_name=b'Contents')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('best_before', models.DateField(help_text=b'The effective date for this note', null=True, blank=True)),
                ('file_attachment', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, null=True, upload_to=advisornotes.models.attachment_upload_to, blank=True)),
                ('file_mediatype', models.CharField(max_length=200, null=True, editable=False, blank=True)),
                ('hidden', models.BooleanField(default=False, db_index=True)),
                ('advisor', models.ForeignKey(editable=False, to='coredata.Person', help_text=b'The advisor that created the note')),
                ('artifact', models.ForeignKey(blank=True, to='advisornotes.Artifact', help_text=b'The artifact that the note is about', null=True)),
                ('course', models.ForeignKey(blank=True, to='coredata.Course', help_text=b'The course that the note is about', null=True)),
                ('course_offering', models.ForeignKey(blank=True, to='coredata.CourseOffering', help_text=b'The course offering that the note is about', null=True)),
                ('unit', models.ForeignKey(help_text=b'The academic unit that owns this note', to='coredata.Unit')),
            ],
            options={
                'ordering': ['created_at'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NonStudent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_name', models.CharField(max_length=32)),
                ('first_name', models.CharField(max_length=32)),
                ('middle_name', models.CharField(max_length=32, null=True, blank=True)),
                ('pref_first_name', models.CharField(max_length=32, null=True, blank=True)),
                ('high_school', models.CharField(max_length=32, null=True, blank=True)),
                ('college', models.CharField(max_length=32, null=True, blank=True)),
                ('start_year', models.IntegerField(help_text=b'The predicted/potential start year', null=True, blank=True)),
                ('notes', models.TextField(help_text=b'Any general information for the student', blank=True)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('unit', models.ForeignKey(blank=True, to='coredata.Unit', help_text=b'The potential academic unit for the student', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='artifact',
            unique_together=set([('name', 'unit')]),
        ),
        migrations.AddField(
            model_name='advisorvisit',
            name='nonstudent',
            field=models.ForeignKey(blank=True, to='advisornotes.NonStudent', help_text=b'The non-student that visited', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='advisorvisit',
            name='program',
            field=models.ForeignKey(related_name='+', blank=True, to='coredata.Unit', help_text=b'The unit of the program the student is in', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='advisorvisit',
            name='student',
            field=models.ForeignKey(related_name='+', blank=True, to='coredata.Person', help_text=b'The student that visited the advisor', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='advisorvisit',
            name='unit',
            field=models.ForeignKey(help_text=b'The academic unit that owns this visit', to='coredata.Unit'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='advisornote',
            name='nonstudent',
            field=models.ForeignKey(editable=False, to='advisornotes.NonStudent', help_text=b'The non-student that the note is about', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='advisornote',
            name='student',
            field=models.ForeignKey(related_name='student', editable=False, to='coredata.Person', help_text=b'The student that the note is about', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='advisornote',
            name='unit',
            field=models.ForeignKey(help_text=b'The academic unit that owns this note', to='coredata.Unit'),
            preserve_default=True,
        ),
    ]
