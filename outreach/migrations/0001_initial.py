# -*- coding: utf-8 -*-


from django.db import migrations, models
import autoslug.fields
import outreach.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('coredata', '0013_auto_20160531_1320'),
    ]

    operations = [
        migrations.CreateModel(
            name='OutreachEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=60)),
                ('start_date', models.DateTimeField(default=outreach.models.timezone_today, help_text=b'Event start date and time.  Use 24h format for the time if needed.', verbose_name=b'Start Date and Time')),
                ('end_date', models.DateTimeField(help_text=b'Event end date and time', verbose_name=b'End Date and Time')),
                ('location', models.CharField(max_length=400, null=True, blank=True)),
                ('description', models.CharField(max_length=400, null=True, blank=True)),
                ('score', models.DecimalField(decimal_places=0, max_length=2, max_digits=2, blank=True, help_text=b'The score according to the event score matrix', null=True)),
                ('resources', models.CharField(help_text=b'Resources needed for this event.', max_length=400, null=True, blank=True)),
                ('cost', models.DecimalField(help_text=b'Cost of this event', null=True, max_digits=8, decimal_places=2, blank=True)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('notes', models.CharField(help_text=b'Special notes to registrants.  These *will* be displayed on the registration forms.', max_length=400, null=True, blank=True)),
                ('email', models.EmailField(help_text=b'Contact email.  Address that will be given to registrants on the registration success page in case they have any questions/problems.', max_length=254, null=True, verbose_name=b'Contact e-mail', blank=True)),
                ('slug', autoslug.fields.AutoSlugField(populate_from=b'autoslug', unique=True, editable=False)),
                ('unit', models.ForeignKey(to='coredata.Unit')),
            ],
        ),
        migrations.CreateModel(
            name='OutreachEventRegistration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('last_name', models.CharField(max_length=32, verbose_name=b'Participant Last Name')),
                ('first_name', models.CharField(max_length=32, verbose_name=b'Participant First Name')),
                ('middle_name', models.CharField(max_length=32, null=True, verbose_name=b'Participant Middle Name', blank=True)),
                ('age', models.DecimalField(null=True, verbose_name=b'Participant Age', max_digits=2, decimal_places=0, blank=True)),
                ('parent_name', models.CharField(max_length=100)),
                ('parent_phone', models.CharField(max_length=15)),
                ('email', models.EmailField(max_length=254, verbose_name=b'Contact E-mail')),
                ('waiver', models.BooleanField(default=False)),
                ('school', models.CharField(max_length=200, null=True, verbose_name=b'Participant School', blank=True)),
                ('hidden', models.BooleanField(default=False, editable=False)),
                ('notes', models.CharField(max_length=400, null=True, verbose_name=b'Allergies/Dietary Restrictions', blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(editable=False)),
                ('attended', models.BooleanField(default=True, editable=False)),
                ('event', models.ForeignKey(to='outreach.OutreachEvent')),
            ],
        ),
    ]
