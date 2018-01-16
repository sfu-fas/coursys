# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import django.core.files.storage
import marking.models


class Migration(migrations.Migration):

    dependencies = [
        ('grades', '0001_initial'),
        ('groups', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityComponent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('max_mark', models.DecimalField(max_digits=8, decimal_places=2)),
                ('title', models.CharField(max_length=30)),
                ('description', models.TextField(max_length=200, null=True, blank=True)),
                ('position', models.IntegerField(default=0, null=True, blank=True)),
                ('deleted', models.BooleanField(default=False, db_index=True)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('numeric_activity', models.ForeignKey(to='grades.NumericActivity')),
            ],
            options={
                'ordering': ['numeric_activity', 'deleted', 'position'],
                'verbose_name_plural': 'Activity Marking Components',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ActivityComponentMark',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.DecimalField(verbose_name=b'Mark', max_digits=8, decimal_places=2)),
                ('comment', models.TextField(max_length=1000, null=True, blank=True)),
                ('activity_component', models.ForeignKey(to='marking.ActivityComponent')),
            ],
            options={
                'ordering': ('activity_component',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ActivityMark',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('overall_comment', models.TextField(max_length=1000, null=True, blank=True)),
                ('late_penalty', models.DecimalField(decimal_places=2, default=0, max_digits=5, blank=True, help_text=b'Percentage to deduct from the total due to late submission', null=True)),
                ('mark_adjustment', models.DecimalField(decimal_places=2, default=0, max_digits=8, blank=True, help_text=b'Points to deduct for any special reasons (may be negative for bonus)', null=True, verbose_name=b'Mark Penalty')),
                ('mark_adjustment_reason', models.TextField(max_length=1000, null=True, verbose_name=b'Mark Penalty Reason', blank=True)),
                ('file_attachment', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, null=True, upload_to=marking.models.attachment_upload_to, blank=True)),
                ('file_mediatype', models.CharField(max_length=200, null=True, blank=True)),
                ('created_by', models.CharField(help_text=b'Userid who gives the mark', max_length=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('mark', models.DecimalField(max_digits=8, decimal_places=2)),
            ],
            options={
                'ordering': ['created_at'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ActivityMark_LetterGrade',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('overall_comment', models.TextField(max_length=1000, null=True, blank=True)),
                ('created_by', models.CharField(help_text=b'Userid who gives the mark', max_length=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('mark', models.CharField(max_length=2, choices=[(b'A+', b'A+ (Excellent performance)'), (b'A', b'A (Excellent performance)'), (b'A-', b'A- (Excellent performance)'), (b'B+', b'B+ (Good performance)'), (b'B', b'B (Good performance)'), (b'B-', b'B- (Good performance)'), (b'C+', b'C+ (Satisfactory performance)'), (b'C', b'C (Satisfactory performance)'), (b'C-', b'C- (Marginal performance)'), (b'D', b'D (Marginal performance)'), (b'F', b'F (Fail. Unsatisfactory Performance)'), (b'N', b'N (Did not write exam or did not complete course)'), (b'P', b'P (Satisfactory performance or better (pass, ungraded))'), (b'DE', b'DE (Deferred grade)'), (b'GN', b'GN (Grade not reported)'), (b'IP', b'IP (In progress)')])),
            ],
            options={
                'ordering': ['created_at'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CommonProblem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=30)),
                ('penalty', models.DecimalField(max_digits=8, decimal_places=2)),
                ('description', models.TextField(max_length=200, null=True, blank=True)),
                ('deleted', models.BooleanField(default=False, db_index=True)),
                ('activity_component', models.ForeignKey(to='marking.ActivityComponent')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupActivityMark',
            fields=[
                ('activitymark_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='marking.ActivityMark')),
                ('group', models.ForeignKey(to='groups.Group')),
                ('numeric_activity', models.ForeignKey(to='grades.NumericActivity')),
            ],
            options={
            },
            bases=('marking.activitymark',),
        ),
        migrations.CreateModel(
            name='GroupActivityMark_LetterGrade',
            fields=[
                ('activitymark_lettergrade_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='marking.ActivityMark_LetterGrade')),
                ('letter_grade', models.CharField(max_length=2, choices=[(b'A+', b'A+ (Excellent performance)'), (b'A', b'A (Excellent performance)'), (b'A-', b'A- (Excellent performance)'), (b'B+', b'B+ (Good performance)'), (b'B', b'B (Good performance)'), (b'B-', b'B- (Good performance)'), (b'C+', b'C+ (Satisfactory performance)'), (b'C', b'C (Satisfactory performance)'), (b'C-', b'C- (Marginal performance)'), (b'D', b'D (Marginal performance)'), (b'F', b'F (Fail. Unsatisfactory Performance)'), (b'N', b'N (Did not write exam or did not complete course)'), (b'P', b'P (Satisfactory performance or better (pass, ungraded))'), (b'DE', b'DE (Deferred grade)'), (b'GN', b'GN (Grade not reported)'), (b'IP', b'IP (In progress)')])),
                ('group', models.ForeignKey(to='groups.Group')),
                ('letter_activity', models.ForeignKey(to='grades.LetterActivity')),
            ],
            options={
            },
            bases=('marking.activitymark_lettergrade',),
        ),
        migrations.CreateModel(
            name='StudentActivityMark',
            fields=[
                ('activitymark_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='marking.ActivityMark')),
                ('numeric_grade', models.ForeignKey(to='grades.NumericGrade')),
            ],
            options={
            },
            bases=('marking.activitymark',),
        ),
        migrations.CreateModel(
            name='StudentActivityMark_LetterGrade',
            fields=[
                ('activitymark_lettergrade_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='marking.ActivityMark_LetterGrade')),
                ('letter_grade', models.ForeignKey(to='grades.LetterGrade', choices=[(b'A+', b'A+ (Excellent performance)'), (b'A', b'A (Excellent performance)'), (b'A-', b'A- (Excellent performance)'), (b'B+', b'B+ (Good performance)'), (b'B', b'B (Good performance)'), (b'B-', b'B- (Good performance)'), (b'C+', b'C+ (Satisfactory performance)'), (b'C', b'C (Satisfactory performance)'), (b'C-', b'C- (Marginal performance)'), (b'D', b'D (Marginal performance)'), (b'F', b'F (Fail. Unsatisfactory Performance)'), (b'N', b'N (Did not write exam or did not complete course)'), (b'P', b'P (Satisfactory performance or better (pass, ungraded))'), (b'DE', b'DE (Deferred grade)'), (b'GN', b'GN (Grade not reported)'), (b'IP', b'IP (In progress)')])),
            ],
            options={
            },
            bases=('marking.activitymark_lettergrade',),
        ),
        migrations.AddField(
            model_name='activitymark_lettergrade',
            name='activity',
            field=models.ForeignKey(to='grades.LetterActivity', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activitymark',
            name='activity',
            field=models.ForeignKey(to='grades.NumericActivity', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activitycomponentmark',
            name='activity_mark',
            field=models.ForeignKey(to='marking.ActivityMark'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='activitycomponentmark',
            unique_together=set([('activity_mark', 'activity_component')]),
        ),
    ]
