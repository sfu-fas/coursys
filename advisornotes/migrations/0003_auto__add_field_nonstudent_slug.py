# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'NonStudent.slug'
        db.add_column('advisornotes_nonstudent', 'slug', self.gf('autoslug.fields.AutoSlugField')(default='', unique_with=(), populate_from=None, max_length=50, unique=True, db_index=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'NonStudent.slug'
        db.delete_column('advisornotes_nonstudent', 'slug')


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
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()', 'db_index': 'True'}),
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
