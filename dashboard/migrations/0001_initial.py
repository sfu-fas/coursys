# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.core.files.storage
import dashboard.models
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('source_app', models.CharField(help_text=b'Application that created the story', max_length=20)),
                ('title', models.CharField(help_text=b'Story title (plain text)', max_length=100)),
                ('content', models.TextField(help_text=b'Main story content (<a href="http://en.wikipedia.org/wiki/Textile_%28markup_language%29">Textile markup</a>)')),
                ('published', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('url', models.URLField(help_text=b'absolute URL for the item: starts with "http://" or "/"', verbose_name=b'URL', blank=True)),
                ('read', models.BooleanField(default=False, help_text=b'The user has marked the story read')),
                ('author', models.ForeignKey(related_name='author', to='coredata.Person', null=True)),
                ('course', models.ForeignKey(to='coredata.CourseOffering', null=True)),
                ('user', models.ForeignKey(related_name='user', to='coredata.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Signature',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sig', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=None, location=b'submitted_files'), max_length=500, upload_to=dashboard.models._sig_upload_to)),
                ('user', models.ForeignKey(to='coredata.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=20, db_index=True)),
                ('value', courselib.json_fields.JSONField(default={})),
                ('user', models.ForeignKey(to='coredata.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='userconfig',
            unique_together=set([('user', 'key')]),
        ),
    ]
