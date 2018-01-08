# -*- coding: utf-8 -*-


from django.db import models, migrations
import time
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('oauth_provider', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsumerInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.IntegerField(default=time.time)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('deactivated', models.BooleanField(default=False)),
                ('consumer', models.ForeignKey(to='oauth_provider.Consumer')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
