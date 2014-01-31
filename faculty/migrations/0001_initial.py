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
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=('person', 'unit'), max_length=50, populate_from='full_title')),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')(null=True)),
            ('comments', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('event_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
            ('flags', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('import_key', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'faculty', ['CareerEvent'])

        # Adding model 'DocumentAttachment'
        db.create_table(u'faculty_documentattachment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('career_event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['faculty.CareerEvent'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('contents', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('mediatype', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
        ))
        db.send_create_signal(u'faculty', ['DocumentAttachment'])

        # Adding model 'MemoTemplate'
        db.create_table(u'faculty_memotemplate', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('event_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('template_text', self.gf('django.db.models.fields.TextField')()),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', to=orm['coredata.Person'])),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=(), max_length=50, populate_from=None)),
        ))
        db.send_create_signal(u'faculty', ['MemoTemplate'])

        # Adding unique constraint on 'MemoTemplate', fields ['unit', 'label']
        db.create_unique(u'faculty_memotemplate', ['unit_id', 'label'])

        # Adding model 'Memo'
        db.create_table(u'faculty_memo', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('career_event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['faculty.CareerEvent'])),
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
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
        ))
        db.send_create_signal(u'faculty', ['Memo'])


    def backwards(self, orm):
        # Removing unique constraint on 'MemoTemplate', fields ['unit', 'label']
        db.delete_unique(u'faculty_memotemplate', ['unit_id', 'label'])

        # Deleting model 'CareerEvent'
        db.delete_table(u'faculty_careerevent')

        # Deleting model 'DocumentAttachment'
        db.delete_table(u'faculty_documentattachment')

        # Deleting model 'MemoTemplate'
        db.delete_table(u'faculty_memotemplate')

        # Deleting model 'Memo'
        db.delete_table(u'faculty_memo')


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
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '8', 'unique': 'True', 'null': 'True', 'db_index': 'True'})
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
            'Meta': {'ordering': "('-start_date', '-end_date', 'title')", 'object_name': 'CareerEvent'},
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'flags': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('person', 'unit')", 'max_length': '50', 'populate_from': "'full_title'"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.documentattachment': {
            'Meta': {'ordering': "('created_at',)", 'object_name': 'DocumentAttachment'},
            'career_event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.CareerEvent']"}),
            'contents': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mediatype': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
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
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'subject': ('django.db.models.fields.TextField', [], {}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.MemoTemplate']", 'null': 'True'}),
            'to_lines': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'faculty.memotemplate': {
            'Meta': {'unique_together': "(('unit', 'label'),)", 'object_name': 'MemoTemplate'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['coredata.Person']"}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'template_text': ('django.db.models.fields.TextField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        }
    }

    complete_apps = ['faculty']