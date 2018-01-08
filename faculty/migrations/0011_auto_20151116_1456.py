# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import faculty.models
import django.core.files.storage


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0008_remove_futureperson_email'),
        ('faculty', '0010_documentattachment_hidden'),
    ]

    operations = [
        migrations.CreateModel(
            name='PositionDocumentAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=250)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'title', unique_with=(b'position',), editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contents', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, upload_to=faculty.models.attachment_upload_to)),
                ('mediatype', models.CharField(max_length=200, null=True, editable=False, blank=True)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('created_by', models.ForeignKey(help_text=b'Document attachment created by.', to='coredata.Person')),
                ('position', models.ForeignKey(related_name='attachments', to='faculty.Position')),
            ],
            options={
                'ordering': ('created_at',),
            },
        ),
        migrations.AlterUniqueTogether(
            name='positiondocumentattachment',
            unique_together=set([('position', 'slug')]),
        ),
    ]
