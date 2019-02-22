# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('marking', '0001_initial'),
        ('grades', '0001_initial'),
        ('coredata', '0001_initial'),
        ('groups', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='gradehistory',
            name='group',
            field=models.ForeignKey(to='groups.Group', help_text=b'If this was a mark for a group, the group.', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gradehistory',
            name='mark',
            field=models.ForeignKey(to='marking.ActivityMark', help_text=b'The ActivityMark object this grade came from, if applicable.', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gradehistory',
            name='member',
            field=models.ForeignKey(to='coredata.Member', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='calletteractivity',
            name='exam_activity',
            field=models.ForeignKey(related_name='exam_activity', to='grades.Activity', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='calletteractivity',
            name='numeric_activity',
            field=models.ForeignKey(related_name='numeric_source', to='grades.NumericActivity', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='offering',
            field=models.ForeignKey(to='coredata.CourseOffering', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='activity',
            unique_together=set([('offering', 'slug')]),
        ),
    ]
