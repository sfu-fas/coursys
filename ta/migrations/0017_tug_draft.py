# Generated by Django 3.2.25 on 2024-08-19 14:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ta', '0016_taevaluation'),
    ]

    operations = [
        migrations.AddField(
            model_name='tug',
            name='draft',
            field=models.BooleanField(default=False),
        ),
    ]
