# Generated by Django 2.2.11 on 2020-07-10 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0023_update_choices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='userid',
            field=models.CharField(blank=True, db_index=True, help_text='SFU Unix userid (i.e. part of SFU email address before the "@").', max_length=32, null=True, unique=True, verbose_name='User ID'),
        ),
    ]