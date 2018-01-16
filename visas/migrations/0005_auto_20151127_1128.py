# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import django.core.files.storage
import visas.models


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0008_remove_futureperson_email'),
        ('visas', '0004_model_cleanup'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisaDocumentAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=250)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'title', unique_with=(b'visa',), editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contents', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, upload_to=visas.models.visa_attachment_upload_to)),
                ('mediatype', models.CharField(max_length=200, null=True, editable=False, blank=True)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('created_by', models.ForeignKey(help_text=b'Document attachment created by.', to='coredata.Person')),
            ],
            options={
                'ordering': ('created_at',),
            },
        ),
        migrations.AlterField(
            model_name='visa',
            name='status',
            field=models.CharField(default=b'', max_length=50, choices=[(b'Citizen', b'Citizen'), (b'Work', b'Work Visa'), (b'Perm Resid', b'Permanent Resident'), (b'Student', b'Student Visa'), (b'Diplomat', b'Diplomat'), (b'Min Permit', b"Minister's Permit"), (b'Other', b'Other Visa'), (b'Visitor', b"Visitor's Visa"), (b'Unknown', b'Not Known'), (b'New CDN', b"'New' Canadian citizen"), (b'Conv Refug', b'Convention Refugee'), (b'Refugee', b'Refugee'), (b'Unknown', b'Non-Canadian, Status Unknown'), (b'No Visa St', b'Non-Canadian, No Visa Status'), (b'Live-in Ca', b'Live-in Caregiver')]),
        ),
        migrations.AddField(
            model_name='visadocumentattachment',
            name='visa',
            field=models.ForeignKey(related_name='attachments', to='visas.Visa'),
        ),
        migrations.AlterUniqueTogether(
            name='visadocumentattachment',
            unique_together=set([('visa', 'slug')]),
        ),
    ]
