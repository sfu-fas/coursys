# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0012_auto_20160126_1416'),
    ]

    operations = [
        migrations.AlterField(
            model_name='combinedoffering',
            name='instr_mode',
            field=models.CharField(default=b'P', max_length=2, choices=[(b'CO', b'Co-Op'), (b'DE', b'Distance Education'), (b'GI', b'Graduate Internship'), (b'P', b'In Person'), (b'PO', b'In Person - Off Campus'), (b'PR', b'Practicum')]),
        ),
        migrations.AlterField(
            model_name='courseoffering',
            name='instr_mode',
            field=models.CharField(default=b'P', help_text=b'The instructional mode of the offering', max_length=2, db_index=True, choices=[(b'CO', b'Co-Op'), (b'DE', b'Distance Education'), (b'GI', b'Graduate Internship'), (b'P', b'In Person'), (b'PO', b'In Person - Off Campus'), (b'PR', b'Practicum')]),
        ),
        migrations.AlterField(
            model_name='meetingtime',
            name='offering',
            field=models.ForeignKey(related_name='meeting_time', to='coredata.CourseOffering'),
        ),
        migrations.AlterField(
            model_name='role',
            name='role',
            field=models.CharField(max_length=4, choices=[(b'ADVS', b'Advisor'), (b'FAC', b'Faculty Member'), (b'SESS', b'Sessional Instructor'), (b'COOP', b'Co-op Staff'), (b'INST', b'Other Instructor'), (b'SUPV', b'Additional Supervisor'), (b'PLAN', b'Planning Administrator'), (b'DISC', b'Discipline Case Administrator'), (b'DICC', b'Discipline Case Filer (email CC)'), (b'ADMN', b'Departmental Administrator'), (b'TAAD', b'TA Administrator'), (b'TADM', b'Teaching Administrator'), (b'GRAD', b'Grad Student Administrator'), (b'GRPD', b'Graduate Program Director'), (b'FUND', b'Grad Funding Administrator'), (b'FDCC', b'Grad Funding Reminder CC'), (b'TECH', b'Tech Staff'), (b'GPA', b'GPA conversion system admin'), (b'OUTR', b'Outreach Administrator'), (b'SYSA', b'System Administrator'), (b'NONE', b'none')]),
        ),
        migrations.AlterField(
            model_name='roleaccount',
            name='type',
            field=models.CharField(blank=True, max_length=4, null=True, choices=[(b'ADVS', b'Advisor'), (b'FAC', b'Faculty Member'), (b'SESS', b'Sessional Instructor'), (b'COOP', b'Co-op Staff'), (b'INST', b'Other Instructor'), (b'SUPV', b'Additional Supervisor'), (b'PLAN', b'Planning Administrator'), (b'DISC', b'Discipline Case Administrator'), (b'DICC', b'Discipline Case Filer (email CC)'), (b'ADMN', b'Departmental Administrator'), (b'TAAD', b'TA Administrator'), (b'TADM', b'Teaching Administrator'), (b'GRAD', b'Grad Student Administrator'), (b'GRPD', b'Graduate Program Director'), (b'FUND', b'Grad Funding Administrator'), (b'FDCC', b'Grad Funding Reminder CC'), (b'TECH', b'Tech Staff'), (b'GPA', b'GPA conversion system admin'), (b'OUTR', b'Outreach Administrator'), (b'SYSA', b'System Administrator'), (b'NONE', b'none')]),
        ),
    ]
