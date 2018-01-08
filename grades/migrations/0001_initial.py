# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Name of the activity.', max_length=30, db_index=True)),
                ('short_name', models.CharField(help_text=b'Short-form name of the activity.', max_length=15, db_index=True)),
                ('slug', autoslug.fields.AutoSlugField(help_text=b'String that identifies this activity within the course offering', editable=False)),
                ('status', models.CharField(help_text=b'Activity status.', max_length=4, choices=[(b'RLS', b'grades released'), (b'URLS', b'grades not released to students'), (b'INVI', b'activity not visible to students')])),
                ('due_date', models.DateTimeField(help_text=b'Activity due date', null=True)),
                ('percent', models.DecimalField(null=True, max_digits=5, decimal_places=2, blank=True)),
                ('position', models.PositiveSmallIntegerField(help_text=b'The order of displaying course activities.')),
                ('group', models.BooleanField(default=False)),
                ('deleted', models.BooleanField(default=False, db_index=True)),
                ('config', courselib.json_fields.JSONField(default={})),
            ],
            options={
                'ordering': ['deleted', 'position'],
                'verbose_name_plural': 'activities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GradeHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('activity_status', models.CharField(help_text=b'Activity status when grade was entered.', max_length=4, choices=[(b'RLS', b'grades released'), (b'URLS', b'grades not released to students'), (b'INVI', b'activity not visible to students')])),
                ('numeric_grade', models.DecimalField(default=0, max_digits=8, decimal_places=2)),
                ('letter_grade', models.CharField(max_length=2, choices=[(b'A+', b'A+ (Excellent performance)'), (b'A', b'A (Excellent performance)'), (b'A-', b'A- (Excellent performance)'), (b'B+', b'B+ (Good performance)'), (b'B', b'B (Good performance)'), (b'B-', b'B- (Good performance)'), (b'C+', b'C+ (Satisfactory performance)'), (b'C', b'C (Satisfactory performance)'), (b'C-', b'C- (Marginal performance)'), (b'D', b'D (Marginal performance)'), (b'F', b'F (Fail. Unsatisfactory Performance)'), (b'N', b'N (Did not write exam or did not complete course)'), (b'P', b'P (Satisfactory performance or better (pass, ungraded))'), (b'DE', b'DE (Deferred grade)'), (b'GN', b'GN (Grade not reported)'), (b'IP', b'IP (In progress)')])),
                ('grade_flag', models.CharField(help_text=b'Status of the grade', max_length=4, choices=[(b'NOGR', b'no grade'), (b'GRAD', b'graded'), (b'CALC', b'calculated'), (b'EXCU', b'excused'), (b'DISH', b'academic dishonesty')])),
                ('comment', models.TextField(null=True)),
                ('status_change', models.BooleanField(default=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LetterActivity',
            fields=[
                ('activity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='grades.Activity')),
            ],
            options={
                'verbose_name_plural': 'letter activities',
            },
            bases=('grades.activity',),
        ),
        migrations.CreateModel(
            name='CalLetterActivity',
            fields=[
                ('letteractivity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='grades.LetterActivity')),
                ('letter_cutoffs', models.CharField(default=b'[95, 90, 85, 80, 75, 70, 65, 60, 55, 50]', help_text=b'parsed formula to calculate final letter grade', max_length=500)),
            ],
            options={
                'verbose_name_plural': 'cal letter activities',
            },
            bases=('grades.letteractivity',),
        ),
        migrations.CreateModel(
            name='LetterGrade',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('letter_grade', models.CharField(max_length=2, choices=[(b'A+', b'A+ (Excellent performance)'), (b'A', b'A (Excellent performance)'), (b'A-', b'A- (Excellent performance)'), (b'B+', b'B+ (Good performance)'), (b'B', b'B (Good performance)'), (b'B-', b'B- (Good performance)'), (b'C+', b'C+ (Satisfactory performance)'), (b'C', b'C (Satisfactory performance)'), (b'C-', b'C- (Marginal performance)'), (b'D', b'D (Marginal performance)'), (b'F', b'F (Fail. Unsatisfactory Performance)'), (b'N', b'N (Did not write exam or did not complete course)'), (b'P', b'P (Satisfactory performance or better (pass, ungraded))'), (b'DE', b'DE (Deferred grade)'), (b'GN', b'GN (Grade not reported)'), (b'IP', b'IP (In progress)')])),
                ('flag', models.CharField(default=b'NOGR', help_text=b'Status of the grade', max_length=4, choices=[(b'NOGR', b'no grade'), (b'GRAD', b'graded'), (b'CALC', b'calculated'), (b'EXCU', b'excused'), (b'DISH', b'academic dishonesty')])),
                ('comment', models.TextField(null=True)),
                ('activity', models.ForeignKey(to='grades.LetterActivity')),
                ('member', models.ForeignKey(to='coredata.Member')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NumericActivity',
            fields=[
                ('activity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='grades.Activity')),
                ('max_grade', models.DecimalField(max_digits=8, decimal_places=2)),
            ],
            options={
                'verbose_name_plural': 'numeric activities',
            },
            bases=('grades.activity',),
        ),
        migrations.CreateModel(
            name='CalNumericActivity',
            fields=[
                ('numericactivity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='grades.NumericActivity')),
                ('formula', models.TextField(default=b'[[activitytotal]]', help_text=b'parsed formula to calculate final numeric grade')),
            ],
            options={
                'verbose_name_plural': 'cal numeric activities',
            },
            bases=('grades.numericactivity',),
        ),
        migrations.CreateModel(
            name='NumericGrade',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.DecimalField(default=0, max_digits=8, decimal_places=2)),
                ('flag', models.CharField(default=b'NOGR', help_text=b'Status of the grade', max_length=4, choices=[(b'NOGR', b'no grade'), (b'GRAD', b'graded'), (b'CALC', b'calculated'), (b'EXCU', b'excused'), (b'DISH', b'academic dishonesty')])),
                ('comment', models.TextField(null=True)),
                ('activity', models.ForeignKey(to='grades.NumericActivity')),
                ('member', models.ForeignKey(to='coredata.Member')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='numericgrade',
            unique_together=set([('activity', 'member')]),
        ),
        migrations.AlterUniqueTogether(
            name='lettergrade',
            unique_together=set([('activity', 'member')]),
        ),
        migrations.AddField(
            model_name='gradehistory',
            name='activity',
            field=models.ForeignKey(to='grades.Activity'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gradehistory',
            name='entered_by',
            field=models.ForeignKey(to='coredata.Person'),
            preserve_default=True,
        ),
    ]
