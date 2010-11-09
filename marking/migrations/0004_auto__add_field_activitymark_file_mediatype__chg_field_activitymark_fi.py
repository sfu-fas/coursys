# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'ActivityMark.file_mediatype'
        db.add_column('marking_activitymark', 'file_mediatype', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True), keep_default=False)

        # Changing field 'ActivityMark.file_attachment'
        db.alter_column('marking_activitymark', 'file_attachment', self.gf('django.db.models.fields.files.FileField')(max_length=500, null=True, blank=True))

        # Changing field 'ActivityMark.mark_adjustment'
        db.alter_column('marking_activitymark', 'mark_adjustment', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True))

        # Changing field 'ActivityMark.late_penalty'
        db.alter_column('marking_activitymark', 'late_penalty', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True))


    def backwards(self, orm):
        
        # Deleting field 'ActivityMark.file_mediatype'
        db.delete_column('marking_activitymark', 'file_mediatype')

        # Changing field 'ActivityMark.file_attachment'
        db.alter_column('marking_activitymark', 'file_attachment', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True))

        # Changing field 'ActivityMark.mark_adjustment'
        db.alter_column('marking_activitymark', 'mark_adjustment', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True))

        # Changing field 'ActivityMark.late_penalty'
        db.alter_column('marking_activitymark', 'late_penalty', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True))


    models = {
        'coredata.courseoffering': {
            'Meta': {'unique_together': "(('semester', 'subject', 'number', 'section'), ('semester', 'crse_id', 'section'), ('semester', 'class_nbr'))", 'object_name': 'CourseOffering'},
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'class_nbr': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'crse_id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'}),
            'enrl_cap': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'enrl_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'graded': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
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
            'Meta': {'object_name': 'Member'},
            'added_reason': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'career': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'credits': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '3'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'person'", 'to': "orm['coredata.Person']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        'coredata.person': {
            'Meta': {'object_name': 'Person'},
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'db_index': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '8', 'unique': 'True', 'null': 'True', 'db_index': 'True'})
        },
        'coredata.semester': {
            'Meta': {'object_name': 'Semester'},
            'end': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        'grades.activity': {
            'Meta': {'object_name': 'Activity'},
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'due_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
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
        'grades.numericactivity': {
            'Meta': {'object_name': 'NumericActivity', '_ormbases': ['grades.Activity']},
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
        },
        'groups.group': {
            'Meta': {'unique_together': "(('name', 'courseoffering'),)", 'object_name': 'Group'},
            'courseoffering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'groupForSemester': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manager': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': "('courseoffering',)", 'db_index': 'True'})
        },
        'marking.activitycomponent': {
            'Meta': {'object_name': 'ActivityComponent'},
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_mark': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'numeric_activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.NumericActivity']"}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'marking.activitycomponentmark': {
            'Meta': {'unique_together': "(('activity_mark', 'activity_component'),)", 'object_name': 'ActivityComponentMark'},
            'activity_component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['marking.ActivityComponent']"}),
            'activity_mark': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['marking.ActivityMark']"}),
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'})
        },
        'marking.activitymark': {
            'Meta': {'object_name': 'ActivityMark'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.NumericActivity']", 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'file_attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'file_mediatype': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'late_penalty': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'mark': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'mark_adjustment': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'mark_adjustment_reason': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'overall_comment': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'})
        },
        'marking.commonproblem': {
            'Meta': {'object_name': 'CommonProblem'},
            'activity_component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['marking.ActivityComponent']"}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'penalty': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'marking.groupactivitymark': {
            'Meta': {'object_name': 'GroupActivityMark', '_ormbases': ['marking.ActivityMark']},
            'activitymark_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['marking.ActivityMark']", 'unique': 'True', 'primary_key': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['groups.Group']"}),
            'numeric_activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.NumericActivity']"})
        },
        'marking.studentactivitymark': {
            'Meta': {'object_name': 'StudentActivityMark', '_ormbases': ['marking.ActivityMark']},
            'activitymark_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['marking.ActivityMark']", 'unique': 'True', 'primary_key': 'True'}),
            'numeric_grade': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.NumericGrade']"})
        }
    }

    complete_apps = ['marking']
