# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CareerEvent'
        db.create_table(u'faculty_careerevent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(related_name='career_events', to=orm['coredata.Person'])),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=('person', 'unit'), max_length=50, populate_from='slug_string')),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('comments', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('event_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
            ('flags', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('status', self.gf('django.db.models.fields.CharField')(default='', max_length=2)),
            ('import_key', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'faculty', ['CareerEvent'])

        # Adding model 'DocumentAttachment'
        db.create_table(u'faculty_documentattachment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('career_event', self.gf('django.db.models.fields.related.ForeignKey')(related_name='attachments', to=orm['faculty.CareerEvent'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=('career_event',), max_length=50, populate_from='title')),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('contents', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('mediatype', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
        ))
        db.send_create_signal(u'faculty', ['DocumentAttachment'])

        # Adding unique constraint on 'DocumentAttachment', fields ['career_event', 'slug']
        db.create_unique(u'faculty_documentattachment', ['career_event_id', 'slug'])

        # Adding model 'MemoTemplate'
        db.create_table(u'faculty_memotemplate', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('event_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('default_from', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('template_text', self.gf('django.db.models.fields.TextField')()),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', to=orm['coredata.Person'])),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
        ))
        db.send_create_signal(u'faculty', ['MemoTemplate'])

        # Adding unique constraint on 'MemoTemplate', fields ['unit', 'label']
        db.create_unique(u'faculty_memotemplate', ['unit_id', 'label'])

        # Adding model 'Memo'
        db.create_table(u'faculty_memo', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('career_event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['faculty.CareerEvent'])),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('sent_date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('to_lines', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('cc_lines', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('from_person', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', null=True, to=orm['coredata.Person'])),
            ('from_lines', self.gf('django.db.models.fields.TextField')()),
            ('subject', self.gf('django.db.models.fields.TextField')()),
            ('template', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['faculty.MemoTemplate'], null=True)),
            ('memo_text', self.gf('django.db.models.fields.TextField')()),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', to=orm['coredata.Person'])),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=('career_event',), max_length=50, populate_from=None)),
        ))
        db.send_create_signal(u'faculty', ['Memo'])

        # Adding model 'EventConfig'
        db.create_table(u'faculty_eventconfig', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('event_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
        ))
        db.send_create_signal(u'faculty', ['EventConfig'])

        # Adding unique constraint on 'EventConfig', fields ['unit', 'event_type']
        db.create_unique(u'faculty_eventconfig', ['unit_id', 'event_type'])

        # Adding model 'TempGrant'
        db.create_table(u'faculty_tempgrant', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('initial', self.gf('django.db.models.fields.DecimalField')(max_digits=12, decimal_places=2)),
            ('project_code', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('import_key', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'], null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
        ))
        db.send_create_signal(u'faculty', ['TempGrant'])

        # Adding unique constraint on 'TempGrant', fields ['label', 'creator']
        db.create_unique(u'faculty_tempgrant', ['label', 'creator_id'])

        # Adding model 'Grant'
        db.create_table(u'faculty_grant', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=('unit',), max_length=50, populate_from='title')),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('project_code', self.gf('django.db.models.fields.CharField')(max_length=32, db_index=True)),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('expiry_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='A', max_length=2)),
            ('initial', self.gf('django.db.models.fields.DecimalField')(max_digits=12, decimal_places=2)),
            ('overhead', self.gf('django.db.models.fields.DecimalField')(max_digits=12, decimal_places=2)),
            ('import_key', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('config', self.gf('jsonfield.fields.JSONField')(default={}, null=True, blank=True)),
        ))
        db.send_create_signal(u'faculty', ['Grant'])

        # Adding unique constraint on 'Grant', fields ['label', 'unit']
        db.create_unique(u'faculty_grant', ['label', 'unit_id'])

        # Adding model 'GrantOwner'
        db.create_table(u'faculty_grantowner', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('grant', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['faculty.Grant'])),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('config', self.gf('jsonfield.fields.JSONField')(default={}, null=True, blank=True)),
        ))
        db.send_create_signal(u'faculty', ['GrantOwner'])

        # Adding model 'GrantBalance'
        db.create_table(u'faculty_grantbalance', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('grant', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['faculty.Grant'])),
            ('balance', self.gf('django.db.models.fields.DecimalField')(max_digits=12, decimal_places=2)),
            ('actual', self.gf('django.db.models.fields.DecimalField')(max_digits=12, decimal_places=2)),
            ('month', self.gf('django.db.models.fields.DecimalField')(max_digits=12, decimal_places=2)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={}, null=True, blank=True)),
        ))
        db.send_create_signal(u'faculty', ['GrantBalance'])

        # Adding model 'FacultyMemberInfo'
        db.create_table(u'faculty_facultymemberinfo', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', unique=True, to=orm['coredata.Person'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('birthday', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('office_number', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('phone_number', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('emergency_contact', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={}, null=True, blank=True)),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'faculty', ['FacultyMemberInfo'])


    def backwards(self, orm):
        # Removing unique constraint on 'Grant', fields ['label', 'unit']
        db.delete_unique(u'faculty_grant', ['label', 'unit_id'])

        # Removing unique constraint on 'TempGrant', fields ['label', 'creator']
        db.delete_unique(u'faculty_tempgrant', ['label', 'creator_id'])

        # Removing unique constraint on 'EventConfig', fields ['unit', 'event_type']
        db.delete_unique(u'faculty_eventconfig', ['unit_id', 'event_type'])

        # Removing unique constraint on 'MemoTemplate', fields ['unit', 'label']
        db.delete_unique(u'faculty_memotemplate', ['unit_id', 'label'])

        # Removing unique constraint on 'DocumentAttachment', fields ['career_event', 'slug']
        db.delete_unique(u'faculty_documentattachment', ['career_event_id', 'slug'])

        # Deleting model 'CareerEvent'
        db.delete_table(u'faculty_careerevent')

        # Deleting model 'DocumentAttachment'
        db.delete_table(u'faculty_documentattachment')

        # Deleting model 'MemoTemplate'
        db.delete_table(u'faculty_memotemplate')

        # Deleting model 'Memo'
        db.delete_table(u'faculty_memo')

        # Deleting model 'EventConfig'
        db.delete_table(u'faculty_eventconfig')

        # Deleting model 'TempGrant'
        db.delete_table(u'faculty_tempgrant')

        # Deleting model 'Grant'
        db.delete_table(u'faculty_grant')

        # Deleting model 'GrantOwner'
        db.delete_table(u'faculty_grantowner')

        # Deleting model 'GrantBalance'
        db.delete_table(u'faculty_grantbalance')

        # Deleting model 'FacultyMemberInfo'
        db.delete_table(u'faculty_facultymemberinfo')


    models = {
        u'coredata.person': {
            'Meta': {'ordering': "['last_name', 'first_name', 'userid']", 'object_name': 'Person'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'db_index': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '8', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'coredata.unit': {
            'Meta': {'ordering': "['label']", 'object_name': 'Unit'},
            'acad_org': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        u'faculty.careerevent': {
            'Meta': {'ordering': "('-start_date', '-end_date', 'event_type')", 'object_name': 'CareerEvent'},
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'flags': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'career_events'", 'to': u"orm['coredata.Person']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('person', 'unit')", 'max_length': '50', 'populate_from': "'slug_string'"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '2'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.documentattachment': {
            'Meta': {'ordering': "('created_at',)", 'unique_together': "(('career_event', 'slug'),)", 'object_name': 'DocumentAttachment'},
            'career_event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': u"orm['faculty.CareerEvent']"}),
            'contents': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mediatype': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('career_event',)", 'max_length': '50', 'populate_from': "'title'"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        },
        u'faculty.eventconfig': {
            'Meta': {'unique_together': "(('unit', 'event_type'),)", 'object_name': 'EventConfig'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.facultymemberinfo': {
            'Meta': {'object_name': 'FacultyMemberInfo'},
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'emergency_contact': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'office_number': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'unique': 'True', 'to': u"orm['coredata.Person']"}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'faculty.grant': {
            'Meta': {'ordering': "['title']", 'unique_together': "(('label', 'unit'),)", 'object_name': 'Grant'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'expiry_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'overhead': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'owners': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['coredata.Person']", 'null': 'True', 'through': u"orm['faculty.GrantOwner']", 'symmetrical': 'False'}),
            'project_code': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('unit',)", 'max_length': '50', 'populate_from': "'title'"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '2'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.grantbalance': {
            'Meta': {'ordering': "['date']", 'object_name': 'GrantBalance'},
            'actual': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'balance': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'grant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.Grant']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'month': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'})
        },
        u'faculty.grantowner': {
            'Meta': {'object_name': 'GrantOwner'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'grant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.Grant']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']"})
        },
        u'faculty.memo': {
            'Meta': {'object_name': 'Memo'},
            'career_event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.CareerEvent']"}),
            'cc_lines': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['coredata.Person']"}),
            'from_lines': ('django.db.models.fields.TextField', [], {}),
            'from_person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['coredata.Person']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memo_text': ('django.db.models.fields.TextField', [], {}),
            'sent_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('career_event',)", 'max_length': '50', 'populate_from': 'None'}),
            'subject': ('django.db.models.fields.TextField', [], {}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.MemoTemplate']", 'null': 'True'}),
            'to_lines': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.memotemplate': {
            'Meta': {'unique_together': "(('unit', 'label'),)", 'object_name': 'MemoTemplate'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['coredata.Person']"}),
            'default_from': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_text': ('django.db.models.fields.TextField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.tempgrant': {
            'Meta': {'unique_together': "(('label', 'creator'),)", 'object_name': 'TempGrant'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'project_code': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        }
    }

    complete_apps = ['faculty']