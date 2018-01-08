# -*- coding: utf-8 -*-


from django.db import migrations, models
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0014_auto_20160623_1509'),
        ('ra', '0007_add_attachments_to_ra_contracts'),
    ]

    operations = [
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('program_number', models.PositiveIntegerField()),
                ('title', models.CharField(max_length=60)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False)),
                ('hidden', models.BooleanField(default=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
            options={
                'ordering': ['program_number'],
            },
        ),
        migrations.AlterField(
            model_name='raappointment',
            name='account',
            field=models.ForeignKey(help_text=b'This is now called "Object" in the new PAF', to='ra.Account'),
        ),
        migrations.AddField(
            model_name='raappointment',
            name='program',
            field=models.ForeignKey(blank=True, to='ra.Program', help_text=b'If none is provided,  "00000" will be added in the PAF', null=True),
        ),
    ]
