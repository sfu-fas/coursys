# -*- coding: utf-8 -*-


from django.db import models, migrations
import faculty.event_types.awards
import bitfield.models
import faculty.event_types.career
import datetime
import faculty.models
import autoslug.fields
import faculty.event_types.info
import faculty.event_types.teaching
import django.core.files.storage
import faculty.event_types.position
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CareerEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(null=True, blank=True)),
                ('comments', models.TextField(blank=True)),
                ('event_type', models.CharField(max_length=10, choices=[(b'ADMINPOS', faculty.event_types.position.AdminPositionEventHandler), (b'APPOINT', faculty.event_types.career.AppointmentEventHandler), (b'AWARD', faculty.event_types.awards.AwardEventHandler), (b'COMMITTEE', faculty.event_types.info.CommitteeMemberHandler), (b'EXTERN_AFF', faculty.event_types.info.ExternalAffiliationHandler), (b'EXTSERVICE', faculty.event_types.info.ExternalServiceHandler), (b'FELLOW', faculty.event_types.awards.FellowshipEventHandler), (b'GRANTAPP', faculty.event_types.awards.GrantApplicationEventHandler), (b'NORM_TEACH', faculty.event_types.teaching.NormalTeachingLoadHandler), (b'LEAVE', faculty.event_types.career.OnLeaveEventHandler), (b'ONE_NINE', faculty.event_types.teaching.OneInNineHandler), (b'OTHER_NOTE', faculty.event_types.info.OtherEventHandler), (b'LABMEMB', faculty.event_types.info.ResearchMembershipHandler), (b'SALARY', faculty.event_types.career.SalaryBaseEventHandler), (b'STIPEND', faculty.event_types.career.SalaryModificationEventHandler), (b'SPCL_DEAL', faculty.event_types.info.SpecialDealHandler), (b'STUDYLEAVE', faculty.event_types.career.StudyLeaveEventHandler), (b'TEACHING', faculty.event_types.awards.TeachingCreditEventHandler), (b'TENUREAPP', faculty.event_types.career.TenureApplicationEventHandler), (b'ACCRED', faculty.event_types.career.AccreditationFlagEventHandler), (b'PROMOTION', faculty.event_types.career.PromotionApplicationEventHandler), (b'SALARYREV', faculty.event_types.career.SalaryReviewEventHandler), (b'CONTRACTRV', faculty.event_types.career.ContractReviewEventHandler)])),
                ('config', courselib.json_fields.JSONField(default={})),
                ('flags', bitfield.models.BitField([b'affects_teaching', b'affects_salary'], default=0)),
                ('status', models.CharField(default=b'', max_length=2, choices=[(b'NA', b'Needs Approval'), (b'A', b'Approved'), (b'D', b'Deleted')])),
                ('import_key', models.TextField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('person', models.ForeignKey(related_name='career_events', to='coredata.Person')),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
                'ordering': ('-start_date', '-end_date', 'event_type'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DocumentAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=250)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contents', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, upload_to=faculty.models.attachment_upload_to)),
                ('mediatype', models.CharField(max_length=200, null=True, editable=False, blank=True)),
                ('career_event', models.ForeignKey(related_name='attachments', to='faculty.CareerEvent')),
                ('created_by', models.ForeignKey(help_text=b'Document attachment created by.', to='coredata.Person')),
            ],
            options={
                'ordering': ('created_at',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('event_type', models.CharField(max_length=10, choices=[(b'ADMINPOS', faculty.event_types.position.AdminPositionEventHandler), (b'APPOINT', faculty.event_types.career.AppointmentEventHandler), (b'AWARD', faculty.event_types.awards.AwardEventHandler), (b'COMMITTEE', faculty.event_types.info.CommitteeMemberHandler), (b'EXTERN_AFF', faculty.event_types.info.ExternalAffiliationHandler), (b'EXTSERVICE', faculty.event_types.info.ExternalServiceHandler), (b'FELLOW', faculty.event_types.awards.FellowshipEventHandler), (b'GRANTAPP', faculty.event_types.awards.GrantApplicationEventHandler), (b'NORM_TEACH', faculty.event_types.teaching.NormalTeachingLoadHandler), (b'LEAVE', faculty.event_types.career.OnLeaveEventHandler), (b'ONE_NINE', faculty.event_types.teaching.OneInNineHandler), (b'OTHER_NOTE', faculty.event_types.info.OtherEventHandler), (b'LABMEMB', faculty.event_types.info.ResearchMembershipHandler), (b'SALARY', faculty.event_types.career.SalaryBaseEventHandler), (b'STIPEND', faculty.event_types.career.SalaryModificationEventHandler), (b'SPCL_DEAL', faculty.event_types.info.SpecialDealHandler), (b'STUDYLEAVE', faculty.event_types.career.StudyLeaveEventHandler), (b'TEACHING', faculty.event_types.awards.TeachingCreditEventHandler), (b'TENUREAPP', faculty.event_types.career.TenureApplicationEventHandler), (b'ACCRED', faculty.event_types.career.AccreditationFlagEventHandler), (b'PROMOTION', faculty.event_types.career.PromotionApplicationEventHandler), (b'SALARYREV', faculty.event_types.career.SalaryReviewEventHandler), (b'CONTRACTRV', faculty.event_types.career.ContractReviewEventHandler)])),
                ('config', courselib.json_fields.JSONField(default={})),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FacultyMemberInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=50)),
                ('birthday', models.DateField(null=True, verbose_name=b'Birthdate', blank=True)),
                ('office_number', models.CharField(max_length=20, null=True, verbose_name=b'Office', blank=True)),
                ('phone_number', models.CharField(max_length=20, null=True, verbose_name=b'Local Phone Number', blank=True)),
                ('emergency_contact', models.TextField(verbose_name=b'Emergency Contact Information', blank=True)),
                ('config', courselib.json_fields.JSONField(default={}, null=True, blank=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('person', models.ForeignKey(related_name='+', to='coredata.Person', unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Grant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text=b'Label for the grant within this system', max_length=64)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('label', models.CharField(help_text=b'for identification from FAST import', max_length=255, db_index=True)),
                ('project_code', models.CharField(help_text=b"The fund and project code, like '13-123456'", max_length=32, db_index=True)),
                ('start_date', models.DateField()),
                ('expiry_date', models.DateField(null=True, blank=True)),
                ('status', models.CharField(default=b'A', max_length=2, choices=[(b'A', b'Active'), (b'D', b'Deleted')])),
                ('initial', models.DecimalField(verbose_name=b'Initial balance', max_digits=12, decimal_places=2)),
                ('overhead', models.DecimalField(help_text=b'Annual overhead returned to Faculty budget', verbose_name=b'Annual overhead', max_digits=12, decimal_places=2)),
                ('import_key', models.CharField(help_text=b"e.g. 'nserc-43517b4fd422423382baab1e916e7f63'", max_length=255, null=True, blank=True)),
                ('config', courselib.json_fields.JSONField(default={}, null=True, blank=True)),
            ],
            options={
                'ordering': ['title'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GrantBalance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(default=datetime.date.today)),
                ('balance', models.DecimalField(verbose_name=b'grant balance', max_digits=12, decimal_places=2)),
                ('actual', models.DecimalField(verbose_name=b'YTD actual', max_digits=12, decimal_places=2)),
                ('month', models.DecimalField(verbose_name=b'current month', max_digits=12, decimal_places=2)),
                ('config', courselib.json_fields.JSONField(default={}, null=True, blank=True)),
                ('grant', models.ForeignKey(to='faculty.Grant')),
            ],
            options={
                'ordering': ['date'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GrantOwner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('config', courselib.json_fields.JSONField(default={}, null=True, blank=True)),
                ('grant', models.ForeignKey(to='faculty.Grant')),
                ('person', models.ForeignKey(to='coredata.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Memo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sent_date', models.DateField(default=datetime.date.today, help_text=b'The sending date of the letter')),
                ('to_lines', models.TextField(help_text=b'Recipient of the memo', null=True, verbose_name=b'Attention', blank=True)),
                ('cc_lines', models.TextField(help_text=b'Additional recipients of the memo', null=True, verbose_name=b'CC lines', blank=True)),
                ('from_lines', models.TextField(help_text=b'Name (and title) of the sender, e.g. "John Smith, Applied Sciences, Dean"', verbose_name=b'From')),
                ('subject', models.TextField(help_text=b'The subject of the memo (lines will be formatted separately in the memo header)')),
                ('memo_text', models.TextField(help_text=b"I.e. 'Congratulations on ... '")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('hidden', models.BooleanField(default=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('career_event', models.ForeignKey(to='faculty.CareerEvent')),
                ('created_by', models.ForeignKey(related_name='+', to='coredata.Person', help_text=b'Letter generation requested by.')),
                ('from_person', models.ForeignKey(related_name='+', to='coredata.Person', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MemoTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(help_text=b'The name for this template (that you select it by when using it)', max_length=250, verbose_name=b'Template Name')),
                ('event_type', models.CharField(help_text=b'The type of event that this memo applies to', max_length=10, choices=[(b'ADMINPOS', faculty.event_types.position.AdminPositionEventHandler), (b'APPOINT', faculty.event_types.career.AppointmentEventHandler), (b'AWARD', faculty.event_types.awards.AwardEventHandler), (b'COMMITTEE', faculty.event_types.info.CommitteeMemberHandler), (b'EXTERN_AFF', faculty.event_types.info.ExternalAffiliationHandler), (b'EXTSERVICE', faculty.event_types.info.ExternalServiceHandler), (b'FELLOW', faculty.event_types.awards.FellowshipEventHandler), (b'GRANTAPP', faculty.event_types.awards.GrantApplicationEventHandler), (b'NORM_TEACH', faculty.event_types.teaching.NormalTeachingLoadHandler), (b'LEAVE', faculty.event_types.career.OnLeaveEventHandler), (b'ONE_NINE', faculty.event_types.teaching.OneInNineHandler), (b'OTHER_NOTE', faculty.event_types.info.OtherEventHandler), (b'LABMEMB', faculty.event_types.info.ResearchMembershipHandler), (b'SALARY', faculty.event_types.career.SalaryBaseEventHandler), (b'STIPEND', faculty.event_types.career.SalaryModificationEventHandler), (b'SPCL_DEAL', faculty.event_types.info.SpecialDealHandler), (b'STUDYLEAVE', faculty.event_types.career.StudyLeaveEventHandler), (b'TEACHING', faculty.event_types.awards.TeachingCreditEventHandler), (b'TENUREAPP', faculty.event_types.career.TenureApplicationEventHandler), (b'ACCRED', faculty.event_types.career.AccreditationFlagEventHandler), (b'PROMOTION', faculty.event_types.career.PromotionApplicationEventHandler), (b'SALARYREV', faculty.event_types.career.SalaryReviewEventHandler), (b'CONTRACTRV', faculty.event_types.career.ContractReviewEventHandler)])),
                ('default_from', models.CharField(help_text=b'The default sender of the memo', max_length=255, verbose_name=b'Default From', blank=True)),
                ('subject', models.CharField(help_text=b'The default subject of the memo', max_length=255, verbose_name=b'Default Subject')),
                ('template_text', models.TextField(help_text=b"The template for the memo. It may be edited when creating each memo. (i.e. 'Congratulations {{first_name}} on ... ')")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('hidden', models.BooleanField(default=False)),
                ('slug', autoslug.fields.AutoSlugField(unique=True, editable=False)),
                ('created_by', models.ForeignKey(related_name='+', to='coredata.Person', help_text=b'Memo template created by.')),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TempGrant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(help_text=b'for identification from FAST import', max_length=255)),
                ('initial', models.DecimalField(verbose_name=b'initial balance', max_digits=12, decimal_places=2)),
                ('project_code', models.CharField(help_text=b"The fund and project code, like '13-123456'", max_length=32)),
                ('import_key', models.CharField(help_text=b"e.g. 'nserc-43517b4fd422423382baab1e916e7f63'", max_length=255, null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('creator', models.ForeignKey(blank=True, to='coredata.Person', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='tempgrant',
            unique_together=set([('label', 'creator')]),
        ),
        migrations.AlterUniqueTogether(
            name='memotemplate',
            unique_together=set([('unit', 'label')]),
        ),
        migrations.AddField(
            model_name='memo',
            name='template',
            field=models.ForeignKey(to='faculty.MemoTemplate', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='memo',
            name='unit',
            field=models.ForeignKey(help_text=b'The unit producing the memo: will determine the letterhead used for the memo.', to='coredata.Unit'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='grant',
            name='owners',
            field=models.ManyToManyField(help_text=b'Who owns/controls this grant?', to='coredata.Person', null=True, through='faculty.GrantOwner'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='grant',
            name='unit',
            field=models.ForeignKey(help_text=b'Unit who owns the grant', to='coredata.Unit'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='grant',
            unique_together=set([('label', 'unit')]),
        ),
        migrations.AlterUniqueTogether(
            name='eventconfig',
            unique_together=set([('unit', 'event_type')]),
        ),
        migrations.AlterUniqueTogether(
            name='documentattachment',
            unique_together=set([('career_event', 'slug')]),
        ),
        migrations.AlterUniqueTogether(
            name='careerevent',
            unique_together=set([('person', 'slug')]),
        ),
    ]
