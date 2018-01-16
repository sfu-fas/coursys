# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import discipline.models
import django.core.files.storage


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CaseAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Identifying name for the attachment', max_length=255, null=True, verbose_name=b'Name', blank=True)),
                ('attachment', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), upload_to=discipline.models._disc_upload_to, max_length=500, verbose_name=b'File')),
                ('mediatype', models.CharField(max_length=200, null=True, blank=True)),
                ('public', models.BooleanField(default=True, help_text=b'Public files will be included in correspondence with student. Private files will be retained as information about the case.', verbose_name=b'Public?')),
                ('notes', models.TextField(help_text=b'Notes about this file (private).', null=True, verbose_name=b'Notes', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DisciplineCaseBase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('notes', models.TextField(help_text=b'Notes about the case (private notes, <a href="javascript:textile_popup()">Textile markup</a> and <a href="javascript:substitution_popup()">case substitutions</a> allowed).', null=True, verbose_name=b'Private Notes', blank=True)),
                ('notes_public', models.TextField(help_text=b'Notes about the case (public notes, <a href="javascript:textile_popup()">Textile markup</a> and <a href="javascript:substitution_popup()">case substitutions</a> allowed).', null=True, verbose_name=b'Public Notes', blank=True)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('contact_email_text', models.TextField(help_text='The initial email sent to the student regarding the case. Please also note the date of the email. (<a href="javascript:substitution_popup()">Case substitutions</a> allowed.)', null=True, verbose_name=b'Contact Email Text', blank=True)),
                ('contacted', models.CharField(default=b'NONE', help_text=b'Has the student been informed of the case?', max_length=4, verbose_name=b'Student Contacted?', choices=[(b'NONE', b'Not yet contacted'), (b'MAIL', b'Email student through this system'), (b'OTHR', b'Instructor will contact student (outside of this system)')])),
                ('contact_date', models.DateField(help_text=b'Date of initial contact with student regarding the case.', null=True, verbose_name=b'Initial Contact Date', blank=True)),
                ('response', models.CharField(default=b'WAIT', help_text=b'Has the student responded to the initial contact?', max_length=4, verbose_name=b'Student Response', choices=[(b'WAIT', b'Waiting for response'), (b'NONE', b'No response from student (after a reasonable period of time)'), (b'DECL', b'Student declined to meet'), (b'MAIL', b'Student sent statement by email'), (b'MET', b'Met with student')])),
                ('meeting_date', models.DateField(help_text=b'Date of meeting/email with student.', null=True, verbose_name=b'Meeting/Email Date', blank=True)),
                ('meeting_summary', models.TextField(help_text=b'Summary of the meeting/email with student (included in letter, <a href="javascript:textile_popup()">Textile markup</a> and <a href="javascript:substitution_popup()">case substitutions</a> allowed).', null=True, verbose_name=b'Meeting/Email Summary', blank=True)),
                ('meeting_notes', models.TextField(help_text=b'Notes about the meeting/email with student (private notes, <a href="javascript:textile_popup()">Textile markup</a> and <a href="javascript:substitution_popup()">case substitutions</a> allowed).', null=True, verbose_name=b'Meeting/Email Notes', blank=True)),
                ('facts', models.TextField(help_text=b'Summary of the facts of the case (included in letter, <a href="javascript:textile_popup()">Textile markup</a> and <a href="javascript:substitution_popup()">case substitutions</a> allowed).  This should be a summary of the case from the instructor\'s perspective.', null=True, verbose_name=b'Facts of the Case', blank=True)),
                ('penalty', models.CharField(default=b'WAIT', help_text=b'Penalty assigned by the instructor for this case.', max_length=4, verbose_name=b'Instructor Penalty', choices=[(b'WAIT', b'penalty not yet assigned'), (b'NONE', b'case dropped: no penalty assigned'), (b'WARN', b'give the student a written warning'), (b'REDO', b'require the student to redo the work, or to do supplementary work'), (b'MARK', b'assign a low grade for the work'), (b'ZERO', 'assign a grade of \u201cF\u201d or zero for the work')])),
                ('refer', models.BooleanField(default=False, help_text=b'Refer this case to the Chair/Director?', verbose_name=b'Refer to chair?')),
                ('penalty_reason', models.TextField(help_text=b'Rationale for assigned penalty, or notes/details concerning penalty.  Optional but recommended. (included in letter, <a href="javascript:textile_popup()">Textile markup</a> and <a href="javascript:substitution_popup()">case substitutions</a> allowed)', null=True, verbose_name=b'Penalty Rationale/Details', blank=True)),
                ('letter_review', models.BooleanField(default=False, help_text=b'Has instructor reviewed the letter before sending?', verbose_name=b'Reviewed?')),
                ('letter_sent', models.CharField(default=b'WAIT', help_text=b'Has the letter been sent to the student and Chair/Director?', max_length=4, verbose_name=b'Letter Sent?', choices=[(b'WAIT', b'Not yet sent'), (b'MAIL', b'Letter emailed through this system'), (b'OTHR', b'Instructor will deliver letter (outside of this system)')])),
                ('letter_date', models.DateField(help_text=b"Date instructor's letter was sent to student.", null=True, verbose_name=b'Letter Date', blank=True)),
                ('letter_text', models.TextField(null=True, verbose_name=b'Letter Text', blank=True)),
                ('penalty_implemented', models.BooleanField(default=False, help_text=b'Has instructor implemented the assigned penalty?', verbose_name=b'Penalty Implemented?')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DisciplineCaseChair',
            fields=[
                ('disciplinecasebase_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='discipline.DisciplineCaseBase')),
            ],
            options={
            },
            bases=('discipline.disciplinecasebase',),
        ),
        migrations.CreateModel(
            name='DisciplineCaseChairNonStudent',
            fields=[
                ('disciplinecasechair_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='discipline.DisciplineCaseChair')),
                ('emplid', models.PositiveIntegerField(help_text=b'SFU student number, if known', max_length=9, null=True, verbose_name=b'Student Number', blank=True)),
                ('userid', models.CharField(help_text=b'SFU Unix userid, if known', max_length=8, null=True, blank=True)),
                ('email', models.EmailField(max_length=75)),
                ('last_name', models.CharField(max_length=32)),
                ('first_name', models.CharField(max_length=32)),
            ],
            options={
            },
            bases=('discipline.disciplinecasechair',),
        ),
        migrations.CreateModel(
            name='DisciplineCaseChairStudent',
            fields=[
                ('disciplinecasechair_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='discipline.DisciplineCaseChair')),
                ('student', models.ForeignKey(help_text=b'The student this case concerns.', to='coredata.Person')),
            ],
            options={
            },
            bases=('discipline.disciplinecasechair',),
        ),
        migrations.CreateModel(
            name='DisciplineCaseInstr',
            fields=[
                ('disciplinecasebase_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='discipline.DisciplineCaseBase')),
            ],
            options={
            },
            bases=('discipline.disciplinecasebase',),
        ),
        migrations.CreateModel(
            name='DisciplineCaseInstrNonStudent',
            fields=[
                ('disciplinecaseinstr_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='discipline.DisciplineCaseInstr')),
                ('emplid', models.PositiveIntegerField(help_text=b'SFU student number, if known', max_length=9, null=True, verbose_name=b'Student Number', blank=True)),
                ('userid', models.CharField(help_text=b'SFU Unix userid, if known', max_length=8, null=True, blank=True)),
                ('email', models.EmailField(max_length=75)),
                ('last_name', models.CharField(max_length=32)),
                ('first_name', models.CharField(max_length=32)),
            ],
            options={
            },
            bases=('discipline.disciplinecaseinstr',),
        ),
        migrations.CreateModel(
            name='DisciplineCaseInstrStudent',
            fields=[
                ('disciplinecaseinstr_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='discipline.DisciplineCaseInstr')),
                ('student', models.ForeignKey(help_text=b'The student this case concerns.', to='coredata.Person')),
            ],
            options={
            },
            bases=('discipline.disciplinecaseinstr',),
        ),
        migrations.CreateModel(
            name='DisciplineGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'An arbitrary "name" for this cluster of cases', max_length=60, verbose_name=b'Cluster Name')),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('offering', models.ForeignKey(help_text=b'The course this cluster is associated with', to='coredata.CourseOffering')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DisciplineTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', models.CharField(help_text=b'The field this template applies to', max_length=30, verbose_name=b'Field', choices=[(b'penalty_reason', b'penalty rationale'), (b'facts', b'facts of the case'), (b'meeting_notes', b'student meeting/email notes'), (b'notes_public', b'public notes'), (b'notes', b'private notes'), (b'contact_email_text', b'initial contact email'), (b'response', b'student response details'), (b'meeting_summary', b'student meeting/email summary')])),
                ('label', models.CharField(help_text=b'A short label for the menu of templates', max_length=50, verbose_name=b'Label')),
                ('text', models.TextField(help_text=b'The text for the template.  Templates can contain <a href="javascript:textile_popup()">Textile markup</a> and <a href="javascript:substitution_popup()">case substitutions</a> allowed (except the initial contact email) and substitutions described below.', verbose_name=b'Text')),
            ],
            options={
                'ordering': ('field', 'label'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RelatedObject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, null=True, blank=True)),
                ('notes', models.TextField(null=True, blank=True)),
                ('object_id', models.PositiveIntegerField()),
                ('case', models.ForeignKey(to='discipline.DisciplineCaseBase')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='disciplinetemplate',
            unique_together=set([('field', 'label')]),
        ),
        migrations.AlterUniqueTogether(
            name='disciplinegroup',
            unique_together=set([('name', 'offering')]),
        ),
        migrations.AddField(
            model_name='disciplinecasechair',
            name='instr_case',
            field=models.ForeignKey(to='discipline.DisciplineCaseInstr', help_text=b"The instructor's case that triggered this case"),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='disciplinecasebase',
            name='group',
            field=models.ForeignKey(blank=True, to='discipline.DisciplineGroup', help_text=b'Cluster this case belongs to (if any).', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='disciplinecasebase',
            name='offering',
            field=models.ForeignKey(to='coredata.CourseOffering'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='disciplinecasebase',
            name='owner',
            field=models.ForeignKey(help_text=b'The person who created/owns this case.', to='coredata.Person'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='caseattachment',
            name='case',
            field=models.ForeignKey(to='discipline.DisciplineCaseBase'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='caseattachment',
            unique_together=set([('case', 'name')]),
        ),
    ]
