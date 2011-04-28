# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Activity.config'
        db.add_column('grades_activity', 'config', self.gf('jsonfield.JSONField')(default={}, null=False, blank=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Activity.config'
        db.delete_column('grades_activity', 'config')


    models = {
        'coredata.courseoffering': {
            'Meta': {'ordering': "['-semester', 'subject', 'number', 'section']", 'unique_together': "(('semester', 'subject', 'number', 'section'), ('semester', 'crse_id', 'section'), ('semester', 'class_nbr'))", 'object_name': 'CourseOffering'},
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'class_nbr': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'config': ('jsonfield.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'crse_id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'}),
            'department': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'enrl_cap': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'enrl_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'graded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'member'", 'symmetrical': 'False', 'through': "orm['coredata.Member']", 'to': "orm['coredata.Person']"}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': '()', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'}),
            'wait_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'coredata.member': {
            'Meta': {'ordering': "['offering', 'person']", 'object_name': 'Member'},
            'added_reason': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'career': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'credits': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '3'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'person'", 'to': "orm['coredata.Person']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        'coredata.person': {
            'Meta': {'ordering': "['last_name', 'first_name', 'userid']", 'object_name': 'Person'},
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'db_index': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '8', 'unique': 'True', 'null': 'True', 'db_index': 'True'})
        },
        'coredata.semester': {
            'Meta': {'ordering': "['name']", 'object_name': 'Semester'},
            'end': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        'grades.activity': {
            'Meta': {'ordering': "['deleted', 'position']", 'object_name': 'Activity'},
            'config': ('jsonfield.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'due_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'db_index': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'percent': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '15', 'db_index': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': "('offering',)", 'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'})
        },
        'grades.calletteractivity': {
            'Meta': {'ordering': "['deleted', 'position']", 'object_name': 'CalLetterActivity', '_ormbases': ['grades.LetterActivity']},
            'exam_activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'exam_activity'", 'null': 'True', 'to': "orm['grades.Activity']"}),
            'letter_cutoffs': ('django.db.models.fields.CharField', [], {'default': "'[95, 90, 85, 80, 75, 70, 65, 60, 55, 50]'", 'max_length': '500'}),
            'letteractivity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['grades.LetterActivity']", 'unique': 'True', 'primary_key': 'True'}),
            'numeric_activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'numeric_source'", 'to': "orm['grades.NumericActivity']"})
        },
        'grades.calnumericactivity': {
            'Meta': {'ordering': "['deleted', 'position']", 'object_name': 'CalNumericActivity', '_ormbases': ['grades.NumericActivity']},
            'formula': ('django.db.models.fields.TextField', [], {'default': "'[[activitytotal]]'"}),
            'numericactivity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['grades.NumericActivity']", 'unique': 'True', 'primary_key': 'True'})
        },
        'grades.letteractivity': {
            'Meta': {'ordering': "['deleted', 'position']", 'object_name': 'LetterActivity', '_ormbases': ['grades.Activity']},
            'activity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['grades.Activity']", 'unique': 'True', 'primary_key': 'True'})
        },
        'grades.lettergrade': {
            'Meta': {'unique_together': "(('activity', 'member'),)", 'object_name': 'LetterGrade'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.LetterActivity']"}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'flag': ('django.db.models.fields.CharField', [], {'default': "'NOGR'", 'max_length': '4'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'letter_grade': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"})
        },
        'grades.numericactivity': {
            'Meta': {'ordering': "['deleted', 'position']", 'object_name': 'NumericActivity', '_ormbases': ['grades.Activity']},
            'activity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['grades.Activity']", 'unique': 'True', 'primary_key': 'True'}),
            'max_grade': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'})
        },
        'grades.numericgrade': {
            'Meta': {'unique_together': "(('activity', 'member'),)", 'object_name': 'NumericGrade'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.NumericActivity']"}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'flag': ('django.db.models.fields.CharField', [], {'default': "'NOGR'", 'max_length': '4'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"}),
            'value': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '5', 'decimal_places': '2'})
        }
    }

    complete_apps = ['grades']
