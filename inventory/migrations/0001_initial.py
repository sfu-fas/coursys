# -*- coding: utf-8 -*-


from django.db import migrations, models
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0014_auto_20160623_1509'),
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=150)),
                ('brand', models.CharField(max_length=60, null=True, blank=True)),
                ('description', models.CharField(max_length=400, null=True, blank=True)),
                ('serial', models.CharField(max_length=60, null=True, verbose_name=b'Serial Number', blank=True)),
                ('tag', models.CharField(help_text=b'SFU Asset Tag number, if it exists', max_length=60, null=True, verbose_name=b'Asset Tag Number', blank=True)),
                ('notes', models.CharField(max_length=400, null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(editable=False)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False)),
                ('unit', models.ForeignKey(help_text=b'Unit to which this asset belongs', to='coredata.Unit')),
            ],
        ),
    ]
