# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import submission.models.base
import submission.models.office
import django.core.files.storage


class Migration(migrations.Migration):

    dependencies = [
        ('grades', '0001_initial'),
        ('coredata', '0001_initial'),
        ('groups', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(default=b'NEW', max_length=3, choices=[(b'NEW', b'New'), (b'INP', b'In-Progress'), (b'DON', b'Marked')])),
            ],
            options={
                'ordering': ['-created_at'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StudentSubmission',
            fields=[
                ('submission_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.Submission', on_delete=models.CASCADE)),
                ('member', models.ForeignKey(to='coredata.Member', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('submission.submission',),
        ),
        migrations.CreateModel(
            name='GroupSubmission',
            fields=[
                ('submission_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.Submission', on_delete=models.CASCADE)),
                ('creator', models.ForeignKey(to='coredata.Member', on_delete=models.CASCADE)),
                ('group', models.ForeignKey(to='groups.Group', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('submission.submission',),
        ),
        migrations.CreateModel(
            name='SubmissionComponent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text=b'Name for this component (e.g. "Part 1" or "Programming Section")', max_length=100)),
                ('description', models.CharField(help_text=b'Short explanation for this component.', max_length=1000, null=True, blank=True)),
                ('position', models.PositiveSmallIntegerField(help_text=b'The order of display for listing components.', null=True, blank=True)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('deleted', models.BooleanField(default=False, help_text=b"Component is invisible to students and can't be submitted if checked.")),
                ('specified_filename', models.CharField(help_text=b'Specify a file name for this component.', max_length=200)),
            ],
            options={
                'ordering': ['position'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PDFComponent',
            fields=[
                ('submissioncomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmissionComponent', on_delete=models.CASCADE)),
                ('max_size', submission.models.base.FileSizeField(default=5000, help_text=b'Maximum size of the PDF file, in kB.')),
            ],
            options={
            },
            bases=('submission.submissioncomponent',),
        ),
        migrations.CreateModel(
            name='OfficeComponent',
            fields=[
                ('submissioncomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmissionComponent', on_delete=models.CASCADE)),
                ('max_size', submission.models.base.FileSizeField(default=10000, help_text=b'Maximum size of the Office file, in kB.')),
                ('allowed', submission.models.office.JSONFieldFlexible(help_text=b'Accepted file extensions.', max_length=500, verbose_name=b'Allowed types')),
            ],
            options={
            },
            bases=('submission.submissioncomponent',),
        ),
        migrations.CreateModel(
            name='ImageComponent',
            fields=[
                ('submissioncomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmissionComponent', on_delete=models.CASCADE)),
                ('max_size', submission.models.base.FileSizeField(default=1000, help_text=b'Maximum size of the image file, in kB.')),
            ],
            options={
            },
            bases=('submission.submissioncomponent',),
        ),
        migrations.CreateModel(
            name='CodefileComponent',
            fields=[
                ('submissioncomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmissionComponent', on_delete=models.CASCADE)),
                ('max_size', submission.models.base.FileSizeField(default=500, help_text=b'Maximum size of the file, in kB.')),
                ('filename', models.CharField(help_text=b'Required filename for submitted files. Interpreted as specified in the filename type', max_length=500, blank=True)),
                ('filename_type', models.CharField(default=b'INS', help_text=b'How should your filename be interpreted?', max_length=3, choices=[(b'INS', b"Filename must match, but uppercase and lowercase don't matter"), (b'MAT', b'Filename must match exactly'), (b'EXT', b'File Extension: the filename must end as specified'), (b'REX', b'Regular Expression: the "filename" above must be a regular expression to match')])),
            ],
            options={
            },
            bases=('submission.submissioncomponent',),
        ),
        migrations.CreateModel(
            name='CodeComponent',
            fields=[
                ('submissioncomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmissionComponent', on_delete=models.CASCADE)),
                ('max_size', submission.models.base.FileSizeField(default=1000, help_text=b'Maximum size of the Code file, in kB.')),
                ('allowed', models.CharField(help_text=b'Accepted file extensions. [Contact system admins if you need more file types here.]', max_length=500, verbose_name=b'Allowed file types')),
            ],
            options={
            },
            bases=('submission.submissioncomponent',),
        ),
        migrations.CreateModel(
            name='ArchiveComponent',
            fields=[
                ('submissioncomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmissionComponent', on_delete=models.CASCADE)),
                ('max_size', submission.models.base.FileSizeField(default=5000, help_text=b'Maximum size of the archive file, in kB.')),
            ],
            options={
            },
            bases=('submission.submissioncomponent',),
        ),
        migrations.CreateModel(
            name='SubmittedComponent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('submit_time', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['submit_time'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubmittedCodefile',
            fields=[
                ('submittedcomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmittedComponent', on_delete=models.CASCADE)),
                ('code', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), upload_to=submission.models.base.submission_upload_path, max_length=500, verbose_name=b'Code submission')),
                ('component', models.ForeignKey(to='submission.CodefileComponent', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('submission.submittedcomponent',),
        ),
        migrations.CreateModel(
            name='SubmittedCode',
            fields=[
                ('submittedcomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmittedComponent', on_delete=models.CASCADE)),
                ('code', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), upload_to=submission.models.base.submission_upload_path, max_length=500, verbose_name=b'Code submission')),
                ('component', models.ForeignKey(to='submission.CodeComponent', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('submission.submittedcomponent',),
        ),
        migrations.CreateModel(
            name='SubmittedArchive',
            fields=[
                ('submittedcomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmittedComponent', on_delete=models.CASCADE)),
                ('archive', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), upload_to=submission.models.base.submission_upload_path, max_length=500, verbose_name=b'Archive submission')),
                ('component', models.ForeignKey(to='submission.ArchiveComponent', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('submission.submittedcomponent',),
        ),
        migrations.CreateModel(
            name='SubmittedImage',
            fields=[
                ('submittedcomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmittedComponent', on_delete=models.CASCADE)),
                ('image', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), upload_to=submission.models.base.submission_upload_path, max_length=500, verbose_name=b'Image submission')),
                ('component', models.ForeignKey(to='submission.ImageComponent', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('submission.submittedcomponent',),
        ),
        migrations.CreateModel(
            name='SubmittedOffice',
            fields=[
                ('submittedcomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmittedComponent', on_delete=models.CASCADE)),
                ('office', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), upload_to=submission.models.base.submission_upload_path, max_length=500, verbose_name=b'Office document submission')),
                ('component', models.ForeignKey(to='submission.OfficeComponent', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('submission.submittedcomponent',),
        ),
        migrations.CreateModel(
            name='SubmittedPDF',
            fields=[
                ('submittedcomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmittedComponent', on_delete=models.CASCADE)),
                ('pdf', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), upload_to=submission.models.base.submission_upload_path, max_length=500, verbose_name=b'PDF submission')),
                ('component', models.ForeignKey(to='submission.PDFComponent', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('submission.submittedcomponent',),
        ),
        migrations.CreateModel(
            name='SubmittedURL',
            fields=[
                ('submittedcomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmittedComponent', on_delete=models.CASCADE)),
                ('url', models.URLField(max_length=500, verbose_name=b'URL submission')),
            ],
            options={
            },
            bases=('submission.submittedcomponent',),
        ),
        migrations.CreateModel(
            name='SubmittedWord',
            fields=[
                ('submittedcomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmittedComponent', on_delete=models.CASCADE)),
                ('word', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), upload_to=submission.models.base.submission_upload_path, max_length=500, verbose_name=b'Word document submission')),
            ],
            options={
            },
            bases=('submission.submittedcomponent',),
        ),
        migrations.CreateModel(
            name='URLComponent',
            fields=[
                ('submissioncomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmissionComponent', on_delete=models.CASCADE)),
                ('check', models.BooleanField(default=False, help_text=b'Check that the page really exists?  Will reject missing or password-protected URLs.')),
                ('prefix', models.CharField(help_text=b'Prefix that the URL *must* start with. (e.g. "http://server.com/course/", blank for none.)', max_length=200, null=True, blank=True)),
            ],
            options={
            },
            bases=('submission.submissioncomponent',),
        ),
        migrations.CreateModel(
            name='WordComponent',
            fields=[
                ('submissioncomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmissionComponent', on_delete=models.CASCADE)),
                ('max_size', submission.models.base.FileSizeField(default=10000, help_text=b'Maximum size of the Word/OpenDoc file, in kB.')),
            ],
            options={
            },
            bases=('submission.submissioncomponent',),
        ),
        migrations.AddField(
            model_name='submittedword',
            name='component',
            field=models.ForeignKey(to='submission.WordComponent', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='submittedurl',
            name='component',
            field=models.ForeignKey(to='submission.URLComponent', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='submittedcomponent',
            name='submission',
            field=models.ForeignKey(to='submission.Submission', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='submissioncomponent',
            name='activity',
            field=models.ForeignKey(to='grades.Activity', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='submission',
            name='activity',
            field=models.ForeignKey(to='grades.Activity', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='submission',
            name='owner',
            field=models.ForeignKey(to='coredata.Member', help_text=b'TA or instructor that will mark this submission', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
