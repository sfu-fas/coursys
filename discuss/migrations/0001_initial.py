# -*- coding: utf-8 -*-


from django.db import models, migrations
import autoslug.fields
import discuss.models
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiscussionMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content', models.TextField(help_text=b'Reply to topic, <a href="http://www.wikicreole.org/wiki/Creole1.0">WikiCreole-formatted</a>')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(default=b'VIS', max_length=3, choices=[(b'VIS', b'Visible'), (b'HID', b'Hidden')])),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('author', models.ForeignKey(to='coredata.Member')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DiscussionSubscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'NONE', help_text=b'Action to take when a new topic is posted', max_length=4, verbose_name=b'Notification', choices=[(b'NONE', b'Do nothing'), (b'MAIL', b'Email me when a new topic is started'), (b'ALLM', b'Email me for new topics and replies')])),
                ('member', models.ForeignKey(to='coredata.Member')),
            ],
            options={
            },
            bases=(models.Model, discuss.models._DiscussionEmailMixin),
        ),
        migrations.CreateModel(
            name='DiscussionTopic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text=b'A brief description of the topic', max_length=140)),
                ('content', models.TextField(help_text=b'The inital message for the topic, <a href="http://www.wikicreole.org/wiki/Creole1.0">WikiCreole-formatted</a>')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_activity_at', models.DateTimeField(auto_now_add=True)),
                ('message_count', models.IntegerField(default=0)),
                ('status', models.CharField(default=b'OPN', help_text=b'The topic status: Closed: no replies allowed, Hidden: cannot be seen', max_length=3, choices=[(b'OPN', b'Open'), (b'ANS', b'Answered'), (b'CLO', b'Closed'), (b'HID', b'Hidden')])),
                ('pinned', models.BooleanField(default=False, help_text=b'Should this topic be pinned to bring attention?')),
                ('slug', autoslug.fields.AutoSlugField(editable=False)),
                ('config', courselib.json_fields.JSONField(default={})),
                ('author', models.ForeignKey(to='coredata.Member')),
                ('offering', models.ForeignKey(to='coredata.CourseOffering')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TopicSubscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'MAIL', help_text=b'Action to take when a new message is posted to this topic', max_length=4, verbose_name=b'Notification', choices=[(b'NONE', b'Do nothing'), (b'MAIL', b'Email me')])),
                ('member', models.ForeignKey(to='coredata.Member')),
                ('topic', models.ForeignKey(to='discuss.DiscussionTopic')),
            ],
            options={
            },
            bases=(models.Model, discuss.models._DiscussionEmailMixin),
        ),
        migrations.AlterUniqueTogether(
            name='topicsubscription',
            unique_together=set([('topic', 'member')]),
        ),
        migrations.AddField(
            model_name='discussionmessage',
            name='topic',
            field=models.ForeignKey(to='discuss.DiscussionTopic'),
            preserve_default=True,
        ),
    ]
