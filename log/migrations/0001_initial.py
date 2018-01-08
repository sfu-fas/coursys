# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LogEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('userid', models.CharField(help_text=b'Userid who made the change', max_length=8, db_index=True)),
                ('datetime', models.DateTimeField(auto_now_add=True)),
                ('description', models.CharField(help_text=b'Description from the system of the change made', max_length=255)),
                ('comment', models.TextField(help_text=b'Comment from the user (if available)', null=True)),
                ('object_id', models.PositiveIntegerField(null=True)),
                ('content_type', models.ForeignKey(related_name='content_type', to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ['-datetime'],
            },
            bases=(models.Model,),
        ),
    ]
