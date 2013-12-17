# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'GradeHistory'
        db.create_table('grades_gradehistory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grades.Activity'])),
            ('member', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Member'])),
            ('entered_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('activity_status', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('numeric_grade', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=8, decimal_places=2)),
            ('letter_grade', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('grade_flag', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('comment', self.gf('django.db.models.fields.TextField')(null=True)),
            ('mark', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['marking.ActivityMark'], null=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['groups.Group'], null=True)),
            ('status_change', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('grades', ['GradeHistory'])


    def backwards(self, orm):
        # Deleting model 'GradeHistory'
        db.delete_table('grades_gradehistory')


    models = {
        'coredata.course': {
            'Meta': {'ordering': "('subject', 'number')", 'unique_together': "(('subject', 'number'),)", 'object_name': 'Course'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'coredata.courseoffering': {
            'Meta': {'ordering': "['-semester', 'subject', 'number', 'section']", 'unique_together': "(('semester', 'subject', 'number', 'section'), ('semester', 'crse_id', 'section'), ('semester', 'class_nbr'))", 'object_name': 'CourseOffering'},
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'class_nbr': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '3', 'db_index': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Course']"}),
            'crse_id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'enrl_cap': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'enrl_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'flags': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'graded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instr_mode': ('django.db.models.fields.CharField', [], {'default': "'P'", 'max_length': '2', 'db_index': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'member'", 'symmetrical': 'False', 'through': "orm['coredata.Member']", 'to': "orm['coredata.Person']"}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']", 'null': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30', 'db_index': 'True'}),
            'wait_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'coredata.member': {
            'Meta': {'ordering': "['offering', 'person']", 'object_name': 'Member'},
            'added_reason': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'career': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'credits': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '3'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'labtut_section': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'official_grade': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'person'", 'to': "orm['coredata.Person']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        'coredata.person': {
            'Meta': {'ordering': "['last_name', 'first_name', 'userid']", 'object_name': 'Person'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'db_index': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '8', 'unique': 'True', 'null': 'True', 'db_index': 'True'})
        },
        'coredata.semester': {
            'Meta': {'ordering': "['name']", 'object_name': 'Semester'},
            'end': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        'coredata.unit': {
            'Meta': {'ordering': "['label']", 'object_name': 'Unit'},
            'acad_org': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        'grades.activity': {
            'Meta': {'ordering': "['deleted', 'position']", 'unique_together': "(('offering', 'slug'),)", 'object_name': 'Activity'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'due_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'db_index': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'percent': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '15', 'db_index': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '4'})
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
        'grades.gradehistory': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'GradeHistory'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.Activity']"}),
            'activity_status': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'entered_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'grade_flag': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['groups.Group']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'letter_grade': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'mark': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['marking.ActivityMark']", 'null': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"}),
            'numeric_grade': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            'status_change': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
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
            'max_grade': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'})
        },
        'grades.numericgrade': {
            'Meta': {'unique_together': "(('activity', 'member'),)", 'object_name': 'NumericGrade'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.NumericActivity']"}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'flag': ('django.db.models.fields.CharField', [], {'default': "'NOGR'", 'max_length': '4'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"}),
            'value': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'})
        },
        'groups.group': {
            'Meta': {'ordering': "['name']", 'unique_together': "(('name', 'courseoffering'), ('slug', 'courseoffering'), ('svn_slug', 'courseoffering'))", 'object_name': 'Group'},
            'courseoffering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'groupForSemester': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manager': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'svn_slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '17', 'unique_with': '()', 'null': 'True', 'populate_from': 'None'})
        },
        'marking.activitymark': {
            'Meta': {'ordering': "['created_at']", 'object_name': 'ActivityMark'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.NumericActivity']", 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'file_attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'file_mediatype': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'late_penalty': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'mark': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'mark_adjustment': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '8', 'decimal_places': '2', 'blank': 'True'}),
            'mark_adjustment_reason': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'overall_comment': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['grades']