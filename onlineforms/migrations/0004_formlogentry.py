# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.utils.timezone
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0003_remove_computingaccount'),
        ('onlineforms', '0003_autoslug'),
    ]

    operations = [
        migrations.CreateModel(
            name='FormLogEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('category', models.CharField(max_length=4, choices=[(b'AUTO', b'Automatic update'), (b'SYST', b'Automatic change by system'), (b'MAIL', b'Email notification sent'), (b'ADMN', b'Administrative action'), (b'FILL', b'User action'), (b'SAVE', b'Saved draft')])),
                ('description', models.CharField(help_text=b'Description of the action/change', max_length=255)),
                ('config', courselib.json_fields.JSONField(default=dict)),
                ('externalFiller', models.ForeignKey(to='onlineforms.NonSFUFormFiller', null=True)),
            ],
            options={
                'ordering': ('timestamp',),
            },
        ),
        migrations.AlterField(
            model_name='formsubmission',
            name='status',
            field=models.CharField(default=b'PEND', max_length=4, choices=[(b'PEND', b'Waiting for the owner to assign a sheet or mark the form completed'), (b'WAIT', b'Waiting for the user to complete their sheet'), (b'DONE', b'No further action required'), (b'REJE', b'Returned incomplete')]),
        ),
        migrations.AlterField(
            model_name='sheetsubmission',
            name='status',
            field=models.CharField(default=b'WAIT', max_length=4, choices=[(b'WAIT', b'Waiting for the user to complete their sheet'), (b'DONE', b'No further action required'), (b'REJE', b'Returned incomplete')]),
        ),
        migrations.AddField(
            model_name='formlogentry',
            name='form_submission',
            field=models.ForeignKey(to='onlineforms.FormSubmission'),
        ),
        migrations.AddField(
            model_name='formlogentry',
            name='sheet_submission',
            field=models.ForeignKey(to='onlineforms.SheetSubmission', null=True),
        ),
        migrations.AddField(
            model_name='formlogentry',
            name='user',
            field=models.ForeignKey(to='coredata.Person', help_text=b'User who took the action/made the change', null=True),
        ),
    ]
