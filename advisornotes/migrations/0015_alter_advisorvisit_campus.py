# Generated by Django 3.2.14 on 2024-01-05 14:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('advisornotes', '0014_advisorvisit_mode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='advisorvisit',
            name='campus',
            field=models.CharField(choices=[('BRNBY', 'Burnaby'), ('SURRY', 'Surrey'), ('VANCR', 'Vancouver'), ('OFFCA', 'Off-Campus')], max_length=5),
        ),
    ]
