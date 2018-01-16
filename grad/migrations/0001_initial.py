# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import datetime
import grad.models
import django.core.files.storage
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompletedRequirement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(help_text=b'Date the requirement was completed (optional)', null=True, blank=True)),
                ('notes', models.TextField(help_text=b'Other notes', null=True, blank=True)),
                ('removed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name=b'Last Updated At')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExternalDocument',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'A short description of what this file contains.', max_length=100)),
                ('file_attachment', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, upload_to=grad.models.attachment_upload_to)),
                ('file_mediatype', models.CharField(max_length=200, editable=False)),
                ('removed', models.BooleanField(default=False)),
                ('date', models.DateField(default=datetime.date.today)),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('comments', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FinancialComment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('comment_type', models.CharField(default=b'OTH', max_length=3, choices=[(b'SCO', b'Scholarship'), (b'TA', b'TA'), (b'RA', b'RA'), (b'OTH', b'Other')])),
                ('comment', models.TextField()),
                ('created_by', models.CharField(help_text=b'Entered by (userid)', max_length=32)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now)),
                ('removed', models.BooleanField(default=False)),
                ('semester', models.ForeignKey(related_name='+', to='coredata.Semester')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GradFlag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(max_length=100)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GradFlagValue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.BooleanField(default=False)),
                ('flag', models.ForeignKey(to='grad.GradFlag')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GradProgram',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(max_length=20)),
                ('description', models.CharField(max_length=100, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name=b'Last Updated At')),
                ('created_by', models.CharField(help_text=b'Grad Program created by.', max_length=32)),
                ('modified_by', models.CharField(help_text=b'Grad Program modified by.', max_length=32, null=True)),
                ('hidden', models.BooleanField(default=False)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GradProgramHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('starting', models.DateField(default=datetime.date.today)),
                ('program', models.ForeignKey(to='grad.GradProgram')),
                ('start_semester', models.ForeignKey(help_text=b'Semester when the student entered the program', to='coredata.Semester')),
            ],
            options={
                'ordering': ('-starting',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GradRequirement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=100)),
                ('series', models.PositiveIntegerField(help_text=b'The category of requirement for searching by requirement, across programs', db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name=b'Last Updated At')),
                ('hidden', models.BooleanField(default=False)),
                ('program', models.ForeignKey(to='grad.GradProgram')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GradStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(max_length=4, choices=[(b'APPL', b'Applicant'), (b'INCO', b'Incomplete Application'), (b'COMP', b'Complete Application'), (b'INRE', b'Application In-Review'), (b'HOLD', b'Hold Application'), (b'OFFO', b'Offer Out'), (b'REJE', b'Rejected Application'), (b'DECL', b'Declined Offer'), (b'EXPI', b'Expired Application'), (b'CONF', b'Confirmed Acceptance'), (b'CANC', b'Cancelled Acceptance'), (b'ARIV', b'Arrived'), (b'ACTI', b'Active'), (b'PART', b'Part-Time'), (b'LEAV', b'On-Leave'), (b'WIDR', b'Withdrawn'), (b'GRAD', b'Graduated'), (b'NOND', b'Non-degree'), (b'GONE', b'Gone'), (b'ARSP', b'Completed Special')])),
                ('start_date', models.DateField(help_text=b'Date this status is effective (optional)', null=True, verbose_name=b'Effective Date', blank=True)),
                ('notes', models.TextField(help_text=b'Other notes', blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('hidden', models.BooleanField(default=False, db_index=True)),
                ('end', models.ForeignKey(related_name='end_semester', blank=True, to='coredata.Semester', help_text=b'Final semester of this status: blank for ongoing', null=True)),
                ('start', models.ForeignKey(related_name='start_semester', verbose_name=b'Effective Semester', to='coredata.Semester', help_text=b'Semester when this status is effective')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GradStudent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('research_area', models.TextField(verbose_name=b'Research Area', blank=True)),
                ('campus', models.CharField(blank=True, max_length=5, db_index=True, choices=[(b'BRNBY', b'Burnaby Campus'), (b'SURRY', b'Surrey Campus'), (b'VANCR', b'Harbour Centre'), (b'OFFST', b'Off-campus'), (b'GNWC', b'Great Northern Way Campus'), (b'METRO', b'Other Locations in Vancouver'), (b'MULTI', b'Multiple Campuses')])),
                ('english_fluency', models.CharField(help_text=b'I.e. Read, Write, Speak, All.', max_length=50, blank=True)),
                ('mother_tongue', models.CharField(help_text=b'I.e. English, Chinese, French', max_length=25, blank=True)),
                ('is_canadian', models.NullBooleanField()),
                ('passport_issued_by', models.CharField(help_text=b'I.e. US, China', max_length=25, blank=True)),
                ('comments', models.TextField(help_text=b'Additional information.', max_length=250, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name=b'Last Updated At')),
                ('created_by', models.CharField(help_text=b'Grad Student created by.', max_length=32)),
                ('modified_by', models.CharField(help_text=b'Grad Student modified by.', max_length=32, null=True, verbose_name=b'Last Modified By')),
                ('current_status', models.CharField(help_text=b'Current student status', max_length=4, null=True, db_index=True, choices=[(b'APPL', b'Applicant'), (b'INCO', b'Incomplete Application'), (b'COMP', b'Complete Application'), (b'INRE', b'Application In-Review'), (b'HOLD', b'Hold Application'), (b'OFFO', b'Offer Out'), (b'REJE', b'Rejected Application'), (b'DECL', b'Declined Offer'), (b'EXPI', b'Expired Application'), (b'CONF', b'Confirmed Acceptance'), (b'CANC', b'Cancelled Acceptance'), (b'ARIV', b'Arrived'), (b'ACTI', b'Active'), (b'PART', b'Part-Time'), (b'LEAV', b'On-Leave'), (b'WIDR', b'Withdrawn'), (b'GRAD', b'Graduated'), (b'NOND', b'Non-degree'), (b'GONE', b'Gone'), (b'ARSP', b'Completed Special')])),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('end_semester', models.ForeignKey(related_name='grad_end_sem', to='coredata.Semester', help_text=b'Semester when the student finished/left the program.', null=True)),
                ('person', models.ForeignKey(help_text=b'Type in student ID or number.', to='coredata.Person')),
                ('program', models.ForeignKey(to='grad.GradProgram')),
                ('start_semester', models.ForeignKey(related_name='grad_start_sem', to='coredata.Semester', help_text=b'Semester when the student started the program.', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Letter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(help_text=b'The sending date of the letter')),
                ('to_lines', models.TextField(help_text=b'Delivery address for the letter', null=True, blank=True)),
                ('content', models.TextField(help_text=b"I.e. 'This is to confirm Mr. Baker ... '")),
                ('closing', models.CharField(default=b'Sincerely', max_length=100)),
                ('from_lines', models.TextField(help_text=b'Name (and title) of the signer, e.g. "John Smith, Program Director"')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.CharField(help_text=b'Letter generation requseted by.', max_length=32)),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('from_person', models.ForeignKey(to='coredata.Person', null=True)),
                ('student', models.ForeignKey(to='grad.GradStudent')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LetterTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(max_length=250)),
                ('content', models.TextField(help_text=b"I.e. 'This is to confirm {{title}} {{last_name}} ... '")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.CharField(help_text=b'Letter template created by.', max_length=32)),
                ('hidden', models.BooleanField(default=False)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OtherFunding',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=100)),
                ('amount', models.DecimalField(verbose_name=b'Funding Amount', max_digits=8, decimal_places=2)),
                ('eligible', models.BooleanField(default=True, help_text=b'Does this funding count towards promises of support?')),
                ('comments', models.TextField(null=True, blank=True)),
                ('removed', models.BooleanField(default=False)),
                ('semester', models.ForeignKey(related_name='other_funding', to='coredata.Semester')),
                ('student', models.ForeignKey(to='grad.GradStudent')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProgressReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('result', models.CharField(db_index=True, max_length=5, choices=[(b'GOOD', b'Good'), (b'SATI', b'Satisfactory'), (b'CONC', b'Satisfactory with Concerns'), (b'UNST', b'Unsatisfactory')])),
                ('removed', models.BooleanField(default=False)),
                ('date', models.DateField(default=datetime.date.today)),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('comments', models.TextField(null=True, blank=True)),
                ('student', models.ForeignKey(to='grad.GradStudent')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Promise',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(verbose_name=b'Promise Amount', max_digits=8, decimal_places=2)),
                ('comments', models.TextField(null=True, blank=True)),
                ('removed', models.BooleanField(default=False)),
                ('end_semester', models.ForeignKey(related_name='promise_end', to='coredata.Semester')),
                ('start_semester', models.ForeignKey(related_name='promise_start', to='coredata.Semester')),
                ('student', models.ForeignKey(to='grad.GradStudent')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SavedSearch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('query', models.TextField()),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('person', models.ForeignKey(to='coredata.Person', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Scholarship',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(verbose_name=b'Scholarship Amount', max_digits=8, decimal_places=2)),
                ('comments', models.TextField(null=True, blank=True)),
                ('removed', models.BooleanField(default=False)),
                ('end_semester', models.ForeignKey(related_name='scholarship_end', to='coredata.Semester')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ScholarshipType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('eligible', models.BooleanField(default=True, help_text=b'Does this scholarship count towards promises of support?')),
                ('comments', models.TextField(null=True, blank=True)),
                ('hidden', models.BooleanField(default=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Supervisor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('external', models.CharField(help_text=b'Details if not an SFU internal member', max_length=200, null=True, blank=True)),
                ('supervisor_type', models.CharField(max_length=3, choices=[(b'SEN', b'Senior Supervisor'), (b'COS', b'Co-senior Supervisor'), (b'COM', b'Committee Member'), (b'CHA', b'Defence Chair'), (b'EXT', b'External Examiner'), (b'SFU', b'SFU Examiner'), (b'POT', b'Potential Supervisor')])),
                ('removed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.CharField(help_text=b'Committee member added by.', max_length=32)),
                ('modified_by', models.CharField(help_text=b'Committee member modified by.', max_length=32, null=True, verbose_name=b'Last Modified By')),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('student', models.ForeignKey(to='grad.GradStudent')),
                ('supervisor', models.ForeignKey(verbose_name=b'Member', blank=True, to='coredata.Person', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='scholarship',
            name='scholarship_type',
            field=models.ForeignKey(to='grad.ScholarshipType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='scholarship',
            name='start_semester',
            field=models.ForeignKey(related_name='scholarship_start', to='coredata.Semester'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='scholarship',
            name='student',
            field=models.ForeignKey(to='grad.GradStudent'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='lettertemplate',
            unique_together=set([('unit', 'label')]),
        ),
        migrations.AddField(
            model_name='letter',
            name='template',
            field=models.ForeignKey(to='grad.LetterTemplate'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gradstatus',
            name='student',
            field=models.ForeignKey(to='grad.GradStudent'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='gradrequirement',
            unique_together=set([('program', 'description')]),
        ),
        migrations.AddField(
            model_name='gradprogramhistory',
            name='student',
            field=models.ForeignKey(to='grad.GradStudent'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='gradprogram',
            unique_together=set([('unit', 'label')]),
        ),
        migrations.AddField(
            model_name='gradflagvalue',
            name='student',
            field=models.ForeignKey(to='grad.GradStudent'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='gradflag',
            unique_together=set([('unit', 'label')]),
        ),
        migrations.AddField(
            model_name='financialcomment',
            name='student',
            field=models.ForeignKey(to='grad.GradStudent'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='externaldocument',
            name='student',
            field=models.ForeignKey(to='grad.GradStudent'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='completedrequirement',
            name='requirement',
            field=models.ForeignKey(to='grad.GradRequirement'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='completedrequirement',
            name='semester',
            field=models.ForeignKey(help_text=b'Semester when the requirement was completed', to='coredata.Semester'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='completedrequirement',
            name='student',
            field=models.ForeignKey(to='grad.GradStudent'),
            preserve_default=True,
        ),
    ]
