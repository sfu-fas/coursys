# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.core.files.storage
import pages.models
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(help_text=b'The &ldquo;filename&rdquo; for this page', max_length=30, db_index=True)),
                ('can_read', models.CharField(default=b'ALL', help_text=b'Who should be able to view this page?', max_length=4, choices=[(b'NONE', b'nobody'), (b'INST', b'instructor'), (b'STAF', b'instructor and TAs'), (b'STUD', b'students, instructor and TAs'), (b'ALL', b'anybody')])),
                ('can_write', models.CharField(default=b'STAF', help_text=b'Who should be able to edit this page?', max_length=4, verbose_name=b'Can change', choices=[(b'NONE', b'nobody'), (b'INST', b'instructor'), (b'STAF', b'instructor and TAs'), (b'STUD', b'students, instructor and TAs')])),
                ('config', courselib.json_fields.JSONField(default={})),
                ('offering', models.ForeignKey(to='coredata.CourseOffering')),
            ],
            options={
                'ordering': ['label'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PageVersion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text=b'The title for the page', max_length=60)),
                ('wikitext', models.TextField(help_text=b'WikiCreole-formatted content of the page')),
                ('diff', models.TextField(null=True, blank=True)),
                ('file_attachment', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, upload_to=pages.models.attachment_upload_to)),
                ('file_mediatype', models.CharField(max_length=200)),
                ('file_name', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.TextField()),
                ('config', courselib.json_fields.JSONField(default={})),
                ('diff_from', models.ForeignKey(to='pages.PageVersion', null=True)),
                ('editor', models.ForeignKey(to='coredata.Member')),
                ('page', models.ForeignKey(to='pages.Page')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='page',
            unique_together=set([('offering', 'label')]),
        ),
    ]
