# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0013_auto_20160531_1320'),
    ]

    operations = [
        migrations.AlterField(
            model_name='role',
            name='role',
            field=models.CharField(max_length=4, choices=[(b'ADVS', b'Advisor'), (b'FAC', b'Faculty Member'), (b'SESS', b'Sessional Instructor'), (b'COOP', b'Co-op Staff'), (b'INST', b'Other Instructor'), (b'SUPV', b'Additional Supervisor'), (b'PLAN', b'Planning Administrator'), (b'DISC', b'Discipline Case Administrator'), (b'DICC', b'Discipline Case Filer (email CC)'), (b'ADMN', b'Departmental Administrator'), (b'TAAD', b'TA Administrator'), (b'TADM', b'Teaching Administrator'), (b'GRAD', b'Grad Student Administrator'), (b'GRPD', b'Graduate Program Director'), (b'FUND', b'Grad Funding Administrator'), (b'FDCC', b'Grad Funding Reminder CC'), (b'TECH', b'Tech Staff'), (b'GPA', b'GPA conversion system admin'), (b'OUTR', b'Outreach Administrator'), (b'INV', b'Inventory Administrator'), (b'SYSA', b'System Administrator'), (b'NONE', b'none')]),
        ),
        migrations.AlterField(
            model_name='roleaccount',
            name='type',
            field=models.CharField(blank=True, max_length=4, null=True, choices=[(b'ADVS', b'Advisor'), (b'FAC', b'Faculty Member'), (b'SESS', b'Sessional Instructor'), (b'COOP', b'Co-op Staff'), (b'INST', b'Other Instructor'), (b'SUPV', b'Additional Supervisor'), (b'PLAN', b'Planning Administrator'), (b'DISC', b'Discipline Case Administrator'), (b'DICC', b'Discipline Case Filer (email CC)'), (b'ADMN', b'Departmental Administrator'), (b'TAAD', b'TA Administrator'), (b'TADM', b'Teaching Administrator'), (b'GRAD', b'Grad Student Administrator'), (b'GRPD', b'Graduate Program Director'), (b'FUND', b'Grad Funding Administrator'), (b'FDCC', b'Grad Funding Reminder CC'), (b'TECH', b'Tech Staff'), (b'GPA', b'GPA conversion system admin'), (b'OUTR', b'Outreach Administrator'), (b'INV', b'Inventory Administrator'), (b'SYSA', b'System Administrator'), (b'NONE', b'none')]),
        ),
    ]
