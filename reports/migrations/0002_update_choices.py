# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hardcodedreport',
            name='file_location',
            field=models.CharField(help_text=b'The location of this report, on disk.', max_length=80, choices=[(b'fas_with_email.py', b'fas_with_email.py'), (b'fas_international.py', b'fas_international.py'), (b'mse_410_less_than_3_coops.py', b'mse_410_less_than_3_coops.py'), (b'five_retakes.py', b'five_retakes.py'), (b'ensc_150_and_250_but_not_215.py', b'ensc_150_and_250_but_not_215.py'), (b'majors_in_courses.py', b'majors_in_courses.py'), (b'bad_gpas.py', b'bad_gpas.py'), (b'cmpt165_after_cmpt.py', b'cmpt165_after_cmpt.py'), (b'enscpro_coop.py', b'enscpro_coop.py'), (b'bad_first_semester.py', b'bad_first_semester.py'), (b'immediate_retake_report.py', b'immediate_retake_report.py'), (b'fake_report.py', b'fake_report.py')]),
            preserve_default=True,
        ),
    ]
