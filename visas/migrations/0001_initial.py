# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Visa',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateField(default=datetime.datetime(2015, 3, 17, 11, 20, 57, 882785), verbose_name=b'Star Date')),
                ('end_date', models.DateField(verbose_name=b'End Date')),
                ('config', courselib.json_fields.JSONField(default={}, editable=False)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('person', models.ForeignKey(to='coredata.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
