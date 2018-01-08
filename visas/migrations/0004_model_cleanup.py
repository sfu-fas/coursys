# -*- coding: utf-8 -*-


from django.db import models, migrations
import visas.models
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('visas', '0003_visa_status'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='visa',
            options={'ordering': ('start_date',)},
        ),
        migrations.AlterField(
            model_name='visa',
            name='config',
            field=courselib.json_fields.JSONField(default=dict, editable=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='visa',
            name='end_date',
            field=models.DateField(help_text=b'Expiry of the visa (if known)', null=True, verbose_name=b'End Date', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='visa',
            name='start_date',
            field=models.DateField(default=visas.models.timezone_today, help_text=b'First day of visa validity', verbose_name=b'Start Date'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='visa',
            name='status',
            field=models.CharField(default=b'', max_length=50, choices=[(b'Citizen', b'Citizen'), (b'Perm Resid', b'Permanent Resident'), (b'Student', b'Student Visa'), (b'Diplomat', b'Diplomat'), (b'Min Permit', b"Minister's Permit"), (b'Other', b'Other Visa'), (b'Visitor', b"Visitor's Visa"), (b'Unknown', b'Not Known'), (b'New CDN', b"'New' Canadian citizen"), (b'Conv Refug', b'Convention Refugee'), (b'Refugee', b'Refugee'), (b'Unknown', b'Non-Canadian, Status Unknown'), (b'No Visa St', b'Non-Canadian, No Visa Status'), (b'Live-in Ca', b'Live-in Caregiver')]),
            preserve_default=True,
        ),
    ]
