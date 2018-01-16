# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
from decimal import Decimal
import django_countries.fields
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ContinuousRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('lookup_lbound', models.DecimalField(verbose_name=b'Lookup lower bound', max_digits=8, decimal_places=2)),
                ('transfer_value', models.CharField(max_length=2, choices=[(b'A+', b'A+ (Excellent performance)'), (b'A', b'A (Excellent performance)'), (b'A-', b'A- (Excellent performance)'), (b'B+', b'B+ (Good performance)'), (b'B', b'B (Good performance)'), (b'B-', b'B- (Good performance)'), (b'C+', b'C+ (Satisfactory performance)'), (b'C', b'C (Satisfactory performance)'), (b'C-', b'C- (Marginal performance)'), (b'D', b'D (Marginal performance)'), (b'F', b'F (Fail. Unsatisfactory Performance)')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DiscreteRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('lookup_value', models.CharField(max_length=64)),
                ('transfer_value', models.CharField(max_length=2, choices=[(b'A+', b'A+ (Excellent performance)'), (b'A', b'A (Excellent performance)'), (b'A-', b'A- (Excellent performance)'), (b'B+', b'B+ (Good performance)'), (b'B', b'B (Good performance)'), (b'B-', b'B- (Good performance)'), (b'C+', b'C+ (Satisfactory performance)'), (b'C', b'C (Satisfactory performance)'), (b'C-', b'C- (Marginal performance)'), (b'D', b'D (Marginal performance)'), (b'F', b'F (Fail. Unsatisfactory Performance)')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GradeSource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('country', django_countries.fields.CountryField(max_length=2)),
                ('institution', models.CharField(max_length=128, verbose_name=b'Institution/Scale Name')),
                ('config', courselib.json_fields.JSONField(default={})),
                ('status', models.CharField(default=b'ACTI', max_length=4, choices=[(b'ACTI', b'Active'), (b'DISA', b'Disabled: invisible to students')])),
                ('scale', models.CharField(default=b'DISC', max_length=4, choices=[(b'DISC', b'Discrete: fixed set of allowed grades'), (b'CONT', b'Continuous: numeric grade range')])),
                ('lower_bound', models.DecimalField(default=Decimal('0.00'), help_text=b'Only used for continuous grade sources', max_digits=8, decimal_places=2)),
                ('upper_bound', models.DecimalField(default=Decimal('100.00'), help_text=b'Only used for continuous grade sources', max_digits=8, decimal_places=2)),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
            ],
            options={
                'ordering': ('institution', 'country'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserArchive',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(unique=True, max_length=64)),
                ('data', courselib.json_fields.JSONField(default={})),
                ('grade_source', models.ForeignKey(to='gpaconvert.GradeSource')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='gradesource',
            unique_together=set([('country', 'institution')]),
        ),
        migrations.AddField(
            model_name='discreterule',
            name='grade_source',
            field=models.ForeignKey(related_name='discrete_rules', to='gpaconvert.GradeSource'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='discreterule',
            unique_together=set([('grade_source', 'lookup_value')]),
        ),
        migrations.AddField(
            model_name='continuousrule',
            name='grade_source',
            field=models.ForeignKey(related_name='continuous_rules', to='gpaconvert.GradeSource'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='continuousrule',
            unique_together=set([('grade_source', 'lookup_lbound')]),
        ),
    ]
