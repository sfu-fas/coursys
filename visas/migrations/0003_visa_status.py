# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('visas', '0002_auto_20150317_1306'),
    ]

    operations = [
        migrations.AddField(
            model_name='visa',
            name='status',
            field=models.CharField(default=b'', max_length=50, choices=[(b'Perm Resid', b'Permanent Resident'), (b'Student', b'Student Visa'), (b'Diplomat', b'Diplomat'), (b'Min Permit', b"Minister's Permit"), (b'Other', b'Other Visa'), (b'Visitor', b"Visitor's Visa"), (b'Unknown', b'Not Known'), (b'New CDN', b"'New' Canadian citizen"), (b'Conv Refug', b'Convention Refugee'), (b'Refugee', b'Refugee'), (b'Unknown', b'Non-Canadian, Status Unknown'), (b'No Visa St', b'Non-Canadian, No Visa Status')]),
            preserve_default=True,
        ),
    ]
