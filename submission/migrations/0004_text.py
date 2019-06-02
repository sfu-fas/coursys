# -*- coding: utf-8 -*-


from django.db import migrations, models
import submission.models.base


class Migration(migrations.Migration):

    dependencies = [
        ('submission', '0003_gittagcomponent_submittedgittag'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubmittedText',
            fields=[
                ('submittedcomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmittedComponent', on_delete=models.CASCADE)),
                ('text', models.TextField(max_length=102400)),
            ],
            bases=('submission.submittedcomponent',),
        ),
        migrations.CreateModel(
            name='TextComponent',
            fields=[
                ('submissioncomponent_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='submission.SubmissionComponent', on_delete=models.CASCADE)),
                ('max_size', submission.models.base.FileSizeField(default=5000, help_text=b'Maximum size of the archive file, in kB.')),
            ],
            bases=('submission.submissioncomponent',),
        ),
        migrations.AddField(
            model_name='submittedtext',
            name='component',
            field=models.ForeignKey(to='submission.TextComponent', on_delete=models.CASCADE),
        ),
    ]
