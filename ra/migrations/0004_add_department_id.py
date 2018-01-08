# -*- coding: utf-8 -*-


from django.db import migrations, models

def set_default_department(apps, schema_editor):
    Project = apps.get_model("ra", "project")
    for project in Project.objects.all():
        if project.department_code == 0:
            project.department_code = project.unit.config.get('deptid') or 0
            project.save()

class Migration(migrations.Migration):

    dependencies = [
        ('ra', '0003_autoslug'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='department_code',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='project',
            name='project_number',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.RunPython(set_default_department)
    ]
