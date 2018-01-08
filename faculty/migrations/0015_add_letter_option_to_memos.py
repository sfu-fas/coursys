# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0014_position_percentage'),
    ]

    operations = [
        migrations.AddField(
            model_name='memo',
            name='is_letter',
            field=models.BooleanField(default=False, help_text=b'Make it a letter with correct letterhead instead of a memo.', verbose_name=b'Make it a letter'),
        ),
        migrations.AddField(
            model_name='memotemplate',
            name='is_letter',
            field=models.BooleanField(default=False, help_text=b'Should this be a letter by default', verbose_name=b'Make it a letter'),
        ),
        migrations.AlterField(
            model_name='memo',
            name='subject',
            field=models.TextField(help_text=b'The subject of the memo (lines will be formatted separately in the memo header). This will be ignored for letters'),
        ),
        migrations.AlterField(
            model_name='memotemplate',
            name='subject',
            field=models.CharField(help_text=b'The default subject of the memo. Will be ignored for letters', max_length=255, verbose_name=b'Default Subject'),
        ),
    ]
