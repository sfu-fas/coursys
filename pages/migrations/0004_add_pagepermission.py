# -*- coding: utf-8 -*-


from django.db import migrations, models
import courselib.json_fields


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0014_auto_20160623_1509'),
        ('pages', '0003_auto_20160104_1203'),
    ]

    operations = [
        migrations.CreateModel(
            name='PagePermission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('role', models.CharField(default=b'STUD', help_text=b'What level of access should this person have for the course?', max_length=4, choices=[(b'INST', b'instructor'), (b'STAF', b'instructor and TAs'), (b'STUD', b'students, instructor and TAs')])),
                ('config', courselib.json_fields.JSONField(default={})),
                ('offering', models.ForeignKey(to='coredata.CourseOffering')),
                ('person', models.ForeignKey(to='coredata.Person')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='pagepermission',
            unique_together=set([('offering', 'person')]),
        ),
    ]
