# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'NonStudent'
        db.create_table('advisornotes_nonstudent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('middle_name', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('pref_first_name', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('high_school', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'], null=True, blank=True)),
            ('config', self.gf('jsonfield.JSONField')(default={})),
        ))
        db.send_create_signal('advisornotes', ['NonStudent'])

        # Adding field 'AdvisorNote.nonstudent'
        db.add_column('advisornotes_advisornote', 'nonstudent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['advisornotes.NonStudent'], null=True), keep_default=False)

        # Changing field 'AdvisorNote.student'
        db.alter_column('advisornotes_advisornote', 'student_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['coredata.Person']))


    def backwards(self, orm):
        
        # Deleting model 'NonStudent'
        db.delete_table('advisornotes_nonstudent')

        # Deleting field 'AdvisorNote.nonstudent'
        db.delete_column('advisornotes_advisornote', 'nonstudent_id')

        # Changing field 'AdvisorNote.student'
        db.alter_column('advisornotes_advisornote', 'student_id', self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['coredata.Person']))


    models = {
        'advisornotes.advisornote': {
            'Meta': {'ordering': "['student', 'created_at']", 'object_name': 'AdvisorNote'},
            'advisor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'advisor'", 'to': "orm['coredata.Person']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file_attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'file_mediatype': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nonstudent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['advisornotes.NonStudent']", 'null': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'student'", 'null': 'True', 'to': "orm['coredata.Person']"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'advisornotes.nonstudent': {
            'Meta': {'object_name': 'NonStudent'},
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'high_school': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']", 'null': 'True', 'blank': 'True'})
        },
        'coredata.person': {
            'Meta': {'ordering': "['last_name', 'first_name', 'userid']", 'object_name': 'Person'},
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'db_index': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '8', 'unique': 'True', 'null': 'True', 'db_index': 'True'})
        },
        'coredata.unit': {
            'Meta': {'ordering': "['label']", 'object_name': 'Unit'},
            'acad_org': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()', 'db_index': 'True'})
        }
    }

    complete_apps = ['advisornotes']
