# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Course'
        db.create_table('planning_course', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=4, db_index=True)),
            ('number', self.gf('django.db.models.fields.CharField')(max_length=4, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('planning', ['Course'])

        # Adding unique constraint on 'Course', fields ['subject', 'number']
        db.create_unique('planning_course', ['subject', 'number'])

        # Adding model 'TeachingCapability'
        db.create_table('planning_teachingcapability', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('instructor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['planning.Course'])),
        ))
        db.send_create_signal('planning', ['TeachingCapability'])

        # Adding unique constraint on 'TeachingCapability', fields ['instructor', 'course']
        db.create_unique('planning_teachingcapability', ['instructor_id', 'course_id'])

        # Adding model 'TeachingIntention'
        db.create_table('planning_teachingintention', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('instructor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Semester'])),
            ('count', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
        ))
        db.send_create_signal('planning', ['TeachingIntention'])

        # Adding unique constraint on 'TeachingIntention', fields ['instructor', 'semester']
        db.create_unique('planning_teachingintention', ['instructor_id', 'semester_id'])

        # Adding model 'PlannedOffering'
        db.create_table('planning_plannedoffering', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['planning.Course'])),
            ('section', self.gf('django.db.models.fields.CharField')(default='', max_length=4, blank=True)),
            ('component', self.gf('django.db.models.fields.CharField')(default='LEC', max_length=3)),
            ('campus', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('enrl_cap', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('instructor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'], null=True, blank=True)),
        ))
        db.send_create_signal('planning', ['PlannedOffering'])

        # Adding unique constraint on 'PlannedOffering', fields ['course', 'section']
        db.create_unique('planning_plannedoffering', ['course_id', 'section'])

        # Adding model 'MeetingTime'
        db.create_table('planning_meetingtime', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('offering', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['planning.PlannedOffering'])),
            ('weekday', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('start_time', self.gf('django.db.models.fields.TimeField')()),
            ('end_time', self.gf('django.db.models.fields.TimeField')()),
            ('room', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('planning', ['MeetingTime'])


    def backwards(self, orm):
        
        # Deleting model 'Course'
        db.delete_table('planning_course')

        # Removing unique constraint on 'Course', fields ['subject', 'number']
        db.delete_unique('planning_course', ['subject', 'number'])

        # Deleting model 'TeachingCapability'
        db.delete_table('planning_teachingcapability')

        # Removing unique constraint on 'TeachingCapability', fields ['instructor', 'course']
        db.delete_unique('planning_teachingcapability', ['instructor_id', 'course_id'])

        # Deleting model 'TeachingIntention'
        db.delete_table('planning_teachingintention')

        # Removing unique constraint on 'TeachingIntention', fields ['instructor', 'semester']
        db.delete_unique('planning_teachingintention', ['instructor_id', 'semester_id'])

        # Deleting model 'PlannedOffering'
        db.delete_table('planning_plannedoffering')

        # Removing unique constraint on 'PlannedOffering', fields ['course', 'section']
        db.delete_unique('planning_plannedoffering', ['course_id', 'section'])

        # Deleting model 'MeetingTime'
        db.delete_table('planning_meetingtime')


    models = {
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
        'planning.course': {
            'Meta': {'unique_together': "(('subject', 'number'),)", 'object_name': 'Course'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'planning.meetingtime': {
            'Meta': {'object_name': 'MeetingTime'},
            'end_time': ('django.db.models.fields.TimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['planning.PlannedOffering']"}),
            'room': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'start_time': ('django.db.models.fields.TimeField', [], {}),
            'weekday': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'planning.plannedoffering': {
            'Meta': {'unique_together': "(('course', 'section'),)", 'object_name': 'PlannedOffering'},
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'component': ('django.db.models.fields.CharField', [], {'default': "'LEC'", 'max_length': '3'}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['planning.Course']"}),
            'enrl_cap': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']", 'null': 'True', 'blank': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '4', 'blank': 'True'})
        },
        'planning.teachingcapability': {
            'Meta': {'unique_together': "(('instructor', 'course'),)", 'object_name': 'TeachingCapability'},
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['planning.Course']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"})
        },
        'planning.teachingintention': {
            'Meta': {'unique_together': "(('instructor', 'semester'),)", 'object_name': 'TeachingIntention'},
            'count': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"})
        }
    }

    complete_apps = ['planning']
