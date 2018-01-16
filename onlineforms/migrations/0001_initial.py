# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import datetime
import django.core.files.storage
import onlineforms.models
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(max_length=60)),
                ('order', models.PositiveIntegerField()),
                ('fieldtype', models.CharField(default=b'SMTX', max_length=4, choices=[(b'SMTX', b'Small Text (single line)'), (b'MDTX', b'Medium Text (a few lines)'), (b'LGTX', b'Large Text (many lines)'), (b'EMAI', b'Email address'), (b'RADI', b'Select with radio buttons'), (b'SEL1', b'Select with a drop-down menu'), (b'SELN', b'Select multiple values'), (b'LIST', b'Enter a list of short responses'), (b'FILE', b'Upload a file'), (b'URL', b'Web page address (URL)'), (b'TEXT', b'Explanation block (user enters nothing)'), (b'DIVI', b'Divider'), (b'DATE', b'A date'), (b'SEM', b'Semester')])),
                ('config', courselib.json_fields.JSONField(default={})),
                ('active', models.BooleanField(default=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('original', models.ForeignKey(blank=True, to='onlineforms.Field', null=True)),
            ],
            options={
            },
            bases=(models.Model, onlineforms.models._FormCoherenceMixin),
        ),
        migrations.CreateModel(
            name='FieldSubmission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('data', courselib.json_fields.JSONField(default={})),
                ('field', models.ForeignKey(to='onlineforms.Field')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FieldSubmissionFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('file_attachment', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, null=True, upload_to=onlineforms.models.attachment_upload_to, blank=True)),
                ('file_mediatype', models.CharField(max_length=200, null=True, editable=False, blank=True)),
                ('field_submission', models.ForeignKey(to='onlineforms.FieldSubmission', unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Form',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text=b'The name of this form.', max_length=60)),
                ('description', models.CharField(help_text=b'A brief description of the form that can be displayed to users.', max_length=500)),
                ('initiators', models.CharField(default=b'NON', help_text=b'Who is allowed to fill out the initial sheet? That is, who can initiate a new instance of this form?', max_length=3, choices=[(b'LOG', b'Logged-in SFU users'), (b'ANY', b'Anyone, including non-SFU users'), (b'NON', b'Nobody: form cannot be filled out')])),
                ('active', models.BooleanField(default=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('advisor_visible', models.BooleanField(default=False, help_text=b'Should submissions be visible to advisors in this unit?')),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('original', models.ForeignKey(blank=True, to='onlineforms.Form', null=True)),
            ],
            options={
            },
            bases=(models.Model, onlineforms.models._FormCoherenceMixin),
        ),
        migrations.CreateModel(
            name='FormFiller',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('config', courselib.json_fields.JSONField(default={})),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FormGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=60)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('config', courselib.json_fields.JSONField(default={})),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FormGroupMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('formgroup', models.ForeignKey(to='onlineforms.FormGroup')),
                ('person', models.ForeignKey(to='coredata.Person')),
            ],
            options={
                'db_table': 'onlineforms_formgroup_members',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FormSubmission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'PEND', max_length=4, choices=[(b'PEND', b'The document is still being worked on'), (b'WAIT', b'Waiting for the owner to send it to someone else or change status to "done"'), (b'DONE', b'No further action required'), (b'REJE', b'Returned incomplete')])),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('form', models.ForeignKey(to='onlineforms.Form')),
                ('initiator', models.ForeignKey(to='onlineforms.FormFiller')),
                ('owner', models.ForeignKey(to='onlineforms.FormGroup')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NonSFUFormFiller',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_name', models.CharField(max_length=32)),
                ('first_name', models.CharField(max_length=32)),
                ('email_address', models.EmailField(max_length=254)),
                ('config', courselib.json_fields.JSONField(default={})),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Sheet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=60)),
                ('order', models.PositiveIntegerField()),
                ('is_initial', models.BooleanField(default=False)),
                ('can_view', models.CharField(default=b'NON', help_text=b'When someone is filling out this sheet, what else can they see?', max_length=4, choices=[(b'ALL', b'Filler can see all info on previous sheets'), (b'NON', b"Filler can't see any info on other sheets (just name/email of initiator)")])),
                ('active', models.BooleanField(default=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('form', models.ForeignKey(to='onlineforms.Form')),
                ('original', models.ForeignKey(blank=True, to='onlineforms.Sheet', null=True)),
            ],
            options={
                'ordering': ('order',),
            },
            bases=(models.Model, onlineforms.models._FormCoherenceMixin),
        ),
        migrations.CreateModel(
            name='SheetSubmission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'WAIT', max_length=4, choices=[(b'WAIT', b'Waiting for the owner to send it to someone else or change status to "done"'), (b'DONE', b'No further action required'), (b'REJE', b'Returned incomplete')])),
                ('given_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(null=True)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('filler', models.ForeignKey(to='onlineforms.FormFiller')),
                ('form_submission', models.ForeignKey(to='onlineforms.FormSubmission')),
                ('sheet', models.ForeignKey(to='onlineforms.Sheet')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SheetSubmissionSecretUrl',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(unique=True, max_length=128, editable=False)),
                ('sheet_submission', models.ForeignKey(to='onlineforms.SheetSubmission')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='sheet',
            unique_together=set([('form', 'slug')]),
        ),
        migrations.AlterUniqueTogether(
            name='formgroupmember',
            unique_together=set([('person', 'formgroup')]),
        ),
        migrations.AddField(
            model_name='formgroup',
            name='members',
            field=models.ManyToManyField(to='coredata.Person', through='onlineforms.FormGroupMember'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='formgroup',
            name='unit',
            field=models.ForeignKey(to='coredata.Unit'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='formgroup',
            unique_together=set([('unit', 'name')]),
        ),
        migrations.AddField(
            model_name='formfiller',
            name='nonSFUFormFiller',
            field=models.ForeignKey(to='onlineforms.NonSFUFormFiller', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='formfiller',
            name='sfuFormFiller',
            field=models.ForeignKey(to='coredata.Person', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='form',
            name='owner',
            field=models.ForeignKey(help_text=b'The group of users who own/administrate this form.', to='onlineforms.FormGroup'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='form',
            name='unit',
            field=models.ForeignKey(to='coredata.Unit'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='fieldsubmission',
            name='sheet_submission',
            field=models.ForeignKey(to='onlineforms.SheetSubmission'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='field',
            name='sheet',
            field=models.ForeignKey(to='onlineforms.Sheet'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='field',
            unique_together=set([('sheet', 'slug')]),
        ),
    ]
