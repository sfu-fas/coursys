# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-10-06 10:25


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('space', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookingrecord',
            name='form_submission_URL',
            field=models.CharField(blank=True, help_text=b'If the user filled in a form to get this booking created, put its URL here.', max_length=1000, null=True),
        ),
        migrations.AddField(
            model_name='roomtype',
            name='space_factor',
            field=models.DecimalField(blank=True, decimal_places=1, default=0.0, max_digits=3),
        ),
        migrations.AlterField(
            model_name='roomtype',
            name='COU_code_value',
            field=models.DecimalField(blank=True, decimal_places=1, help_text=b'e.g. 10.1', max_digits=4, null=True),
        ),
    ]
