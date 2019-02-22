# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('grad', '0002_add_configs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gradstatus',
            name='status',
            field=models.CharField(max_length=4, choices=[(b'INCO', b'Incomplete Application'), (b'COMP', b'Complete Application'), (b'INRE', b'Application In-Review'), (b'HOLD', b'Hold Application'), (b'OFFO', b'Offer Out'), (b'REJE', b'Rejected Application'), (b'DECL', b'Declined Offer'), (b'EXPI', b'Expired Application'), (b'CONF', b'Confirmed Acceptance'), (b'CANC', b'Cancelled Acceptance'), (b'ARIV', b'Arrived'), (b'ACTI', b'Active'), (b'PART', b'Part-Time'), (b'LEAV', b'On-Leave'), (b'WIDR', b'Withdrawn'), (b'GRAD', b'Graduated'), (b'NOND', b'Non-degree'), (b'GONE', b'Gone'), (b'ARSP', b'Completed Special'), (b'TRIN', b'Transferred from another department'), (b'TROU', b'Transferred to another department'), (b'DELE', b'Deleted Record')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='gradstudent',
            name='current_status',
            field=models.CharField(help_text=b'Current student status', max_length=4, null=True, db_index=True, choices=[(b'INCO', b'Incomplete Application'), (b'COMP', b'Complete Application'), (b'INRE', b'Application In-Review'), (b'HOLD', b'Hold Application'), (b'OFFO', b'Offer Out'), (b'REJE', b'Rejected Application'), (b'DECL', b'Declined Offer'), (b'EXPI', b'Expired Application'), (b'CONF', b'Confirmed Acceptance'), (b'CANC', b'Cancelled Acceptance'), (b'ARIV', b'Arrived'), (b'ACTI', b'Active'), (b'PART', b'Part-Time'), (b'LEAV', b'On-Leave'), (b'WIDR', b'Withdrawn'), (b'GRAD', b'Graduated'), (b'NOND', b'Non-degree'), (b'GONE', b'Gone'), (b'ARSP', b'Completed Special'), (b'TRIN', b'Transferred from another department'), (b'TROU', b'Transferred to another department'), (b'DELE', b'Deleted Record')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='supervisor',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime.now),
            preserve_default=True,
        ),
    ]
