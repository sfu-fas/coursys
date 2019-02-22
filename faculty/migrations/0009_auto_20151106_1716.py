# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0008_auto_20151005_1410'),
    ]

    operations = [
        migrations.AlterField(
            model_name='position',
            name='add_pay',
            field=models.DecimalField(null=True, max_digits=10, decimal_places=2, blank=True),
        ),
        migrations.AlterField(
            model_name='position',
            name='add_salary',
            field=models.DecimalField(null=True, max_digits=10, decimal_places=2, blank=True),
        ),
        migrations.AlterField(
            model_name='position',
            name='base_salary',
            field=models.DecimalField(null=True, max_digits=10, decimal_places=2, blank=True),
        ),
        migrations.AlterField(
            model_name='position',
            name='rank',
            field=models.CharField(blank=True, max_length=50, null=True, choices=[(b'LLEC', b'Limited-Term Lecturer'), (b'LABI', b'Laboratory Instructor'), (b'LECT', b'Lecturer'), (b'SLEC', b'Senior Lecturer'), (b'INST', b'Instructor'), (b'ASSI', b'Assistant Professor'), (b'ASSO', b'Associate Professor'), (b'FULL', b'Full Professor'), (b'URAS', b'University Research Associate')]),
        ),
        migrations.AlterField(
            model_name='position',
            name='step',
            field=models.DecimalField(null=True, max_digits=3, decimal_places=1, blank=True),
        ),
    ]
