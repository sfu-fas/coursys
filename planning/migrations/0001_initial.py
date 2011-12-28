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
            ('note', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True)),
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
            ('note', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True)),
            ('intentionfull', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('planning', ['TeachingIntention'])

        # Adding unique constraint on 'TeachingIntention', fields ['instructor', 'semester']
        db.create_unique('planning_teachingintention', ['instructor_id', 'semester_id'])

        # Adding model 'SemesterPlan'
        db.create_table('planning_semesterplan', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Semester'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('visibility', self.gf('django.db.models.fields.CharField')(default='ADMI', max_length=4)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=(), max_length=50, populate_from=None, db_index=True)),
        ))
        db.send_create_signal('planning', ['SemesterPlan'])

        # Adding unique constraint on 'SemesterPlan', fields ['semester', 'name']
        db.create_unique('planning_semesterplan', ['semester_id', 'name'])

        # Adding model 'PlannedOffering'
        db.create_table('planning_plannedoffering', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('plan', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['planning.SemesterPlan'])),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['planning.Course'])),
            ('section', self.gf('django.db.models.fields.CharField')(default='', max_length=4)),
            ('component', self.gf('django.db.models.fields.CharField')(default='LEC', max_length=3)),
            ('campus', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('enrl_cap', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('instructor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'], null=True, blank=True)),
        ))
        db.send_create_signal('planning', ['PlannedOffering'])

        # Adding unique constraint on 'PlannedOffering', fields ['plan', 'course', 'section']
        db.create_unique('planning_plannedoffering', ['plan_id', 'course_id', 'section'])

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
        
        # Removing unique constraint on 'PlannedOffering', fields ['plan', 'course', 'section']
        db.delete_unique('planning_plannedoffering', ['plan_id', 'course_id', 'section'])

        # Removing unique constraint on 'SemesterPlan', fields ['semester', 'name']
        db.delete_unique('planning_semesterplan', ['semester_id', 'name'])

        # Removing unique constraint on 'TeachingIntention', fields ['instructor', 'semester']
        db.delete_unique('planning_teachingintention', ['instructor_id', 'semester_id'])

        # Removing unique constraint on 'TeachingCapability', fields ['instructor', 'course']
        db.delete_unique('planning_teachingcapability', ['instructor_id', 'course_id'])

        # Removing unique constraint on 'Course', fields ['subject', 'number']
        db.delete_unique('planning_course', ['subject', 'number'])

        # Deleting model 'Course'
        db.delete_table('planning_course')

        # Deleting model 'TeachingCapability'
        db.delete_table('planning_teachingcapability')

        # Deleting model 'TeachingIntention'
        db.delete_table('planning_teachingintention')

        # Deleting model 'SemesterPlan'
        db.delete_table('planning_semesterplan')

        # Deleting model 'PlannedOffering'
        db.delete_table('planning_plannedoffering')

        # Deleting model 'MeetingTime'
        db.delete_table('planning_meetingtime')


    models = {
        'coredata.person': {
            'Meta': {'ordering': "['last_name', 'first_name', 'userid']", 'object_name': 'Person'},
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
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
        'planning.course': {
            'Meta': {'ordering': "['subject', 'number']", 'unique_together': "(('subject', 'number'),)", 'object_name': 'Course'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'planning.meetingtime': {
            'Meta': {'ordering': "['offering', 'weekday']", 'object_name': 'MeetingTime'},
            'end_time': ('django.db.models.fields.TimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['planning.PlannedOffering']"}),
            'room': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'start_time': ('django.db.models.fields.TimeField', [], {}),
            'weekday': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'planning.plannedoffering': {
            'Meta': {'ordering': "['plan', 'course', 'campus']", 'unique_together': "(('plan', 'course', 'section'),)", 'object_name': 'PlannedOffering'},
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'component': ('django.db.models.fields.CharField', [], {'default': "'LEC'", 'max_length': '3'}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['planning.Course']"}),
            'enrl_cap': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']", 'null': 'True', 'blank': 'True'}),
            'plan': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['planning.SemesterPlan']"}),
            'section': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '4'})
        },
        'planning.semesterplan': {
            'Meta': {'ordering': "['semester', 'name']", 'unique_together': "(('semester', 'name'),)", 'object_name': 'SemesterPlan'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None', 'db_index': 'True'}),
            'visibility': ('django.db.models.fields.CharField', [], {'default': "'ADMI'", 'max_length': '4'})
        },
        'planning.teachingcapability': {
            'Meta': {'ordering': "['instructor', 'course']", 'unique_together': "(('instructor', 'course'),)", 'object_name': 'TeachingCapability'},
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['planning.Course']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'note': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'})
        },
        'planning.teachingintention': {
            'Meta': {'ordering': "['-semester', 'instructor']", 'unique_together': "(('instructor', 'semester'),)", 'object_name': 'TeachingIntention'},
            'count': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'intentionfull': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'note': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"})
        }
    }

    complete_apps = ['planning']
