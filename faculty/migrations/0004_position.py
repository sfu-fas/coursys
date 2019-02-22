# -*- coding: utf-8 -*-


from django.db import models, migrations
import faculty.models
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0003_autoslug'),
    ]

    operations = [
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100)),
                ('projected_start_date', models.DateField(default=faculty.models.timezone_today, verbose_name=b'Projected Start Date')),
                ('unit', models.CharField(max_length=10)),
                ('position_number', models.CharField(max_length=8)),
                ('rank', models.CharField(max_length=50, choices=[(b'LLEC', b'Limited-Term Lecturer'), (b'LABI', b'Laboratory Instructor'), (b'LECT', b'Lecturer'), (b'SLEC', b'Senior Lecturer'), (b'INST', b'Instructor'), (b'ASSI', b'Assistant Professor'), (b'ASSO', b'Associate Professor'), (b'FULL', b'Full Professor'), (b'URAS', b'University Research Associate')])),
                ('step', models.DecimalField(max_digits=2, decimal_places=0)),
                ('base_salary', models.DecimalField(max_digits=10, decimal_places=2)),
                ('add_salary', models.DecimalField(max_digits=10, decimal_places=2)),
                ('add_pay', models.DecimalField(max_digits=10, decimal_places=2)),
                ('teaching_load', models.DecimalField(max_digits=10, decimal_places=2)),
                ('config', courselib.json_fields.JSONField(default=dict, editable=False)),
                ('hidden', models.BooleanField(default=False, editable=False)),
            ],
            options={
                'ordering': ('projected_start_date', 'title'),
            },
        ),
    ]
