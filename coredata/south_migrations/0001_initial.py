# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Person'
        db.create_table('coredata_person', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('emplid', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True, db_index=True)),
            ('userid', self.gf('django.db.models.fields.CharField')(max_length=8, unique=True, null=True, db_index=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('middle_name', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('pref_first_name', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=4, null=True, blank=True)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
        ))
        db.send_create_signal('coredata', ['Person'])

        # Adding model 'Semester'
        db.create_table('coredata_semester', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=4, db_index=True)),
            ('start', self.gf('django.db.models.fields.DateField')()),
            ('end', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('coredata', ['Semester'])

        # Adding model 'SemesterWeek'
        db.create_table('coredata_semesterweek', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Semester'])),
            ('week', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('monday', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('coredata', ['SemesterWeek'])

        # Adding unique constraint on 'SemesterWeek', fields ['semester', 'week']
        db.create_unique('coredata_semesterweek', ['semester_id', 'week'])

        # Adding model 'Holiday'
        db.create_table('coredata_holiday', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateField')(db_index=True)),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Semester'])),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('holiday_type', self.gf('django.db.models.fields.CharField')(max_length=4)),
        ))
        db.send_create_signal('coredata', ['Holiday'])

        # Adding model 'Course'
        db.create_table('coredata_course', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=4, db_index=True)),
            ('number', self.gf('django.db.models.fields.CharField')(max_length=4, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
        ))
        db.send_create_signal('coredata', ['Course'])

        # Adding unique constraint on 'Course', fields ['subject', 'number']
        db.create_unique('coredata_course', ['subject', 'number'])

        # Adding model 'CourseOffering'
        db.create_table('coredata_courseoffering', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=4, db_index=True)),
            ('number', self.gf('django.db.models.fields.CharField')(max_length=4, db_index=True)),
            ('section', self.gf('django.db.models.fields.CharField')(max_length=4, db_index=True)),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Semester'])),
            ('component', self.gf('django.db.models.fields.CharField')(max_length=3, db_index=True)),
            ('instr_mode', self.gf('django.db.models.fields.CharField')(default='P', max_length=2, db_index=True)),
            ('graded', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'], null=True)),
            ('crse_id', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, db_index=True)),
            ('class_nbr', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=30, db_index=True)),
            ('campus', self.gf('django.db.models.fields.CharField')(max_length=5, db_index=True)),
            ('enrl_cap', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('enrl_tot', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('wait_tot', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('units', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True)),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Course'])),
            ('flags', self.gf('django.db.models.fields.BigIntegerField')(default=0)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
        ))
        db.send_create_signal('coredata', ['CourseOffering'])

        # Adding unique constraint on 'CourseOffering', fields ['semester', 'subject', 'number', 'section']
        db.create_unique('coredata_courseoffering', ['semester_id', 'subject', 'number', 'section'])

        # Adding unique constraint on 'CourseOffering', fields ['semester', 'crse_id', 'section']
        db.create_unique('coredata_courseoffering', ['semester_id', 'crse_id', 'section'])

        # Adding unique constraint on 'CourseOffering', fields ['semester', 'class_nbr']
        db.create_unique('coredata_courseoffering', ['semester_id', 'class_nbr'])

        # Adding model 'Member'
        db.create_table('coredata_member', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(related_name='person', to=orm['coredata.Person'])),
            ('offering', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.CourseOffering'])),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('credits', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=3)),
            ('career', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('added_reason', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('labtut_section', self.gf('django.db.models.fields.CharField')(max_length=4, null=True, blank=True)),
            ('official_grade', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
        ))
        db.send_create_signal('coredata', ['Member'])

        # Adding model 'MeetingTime'
        db.create_table('coredata_meetingtime', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('offering', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.CourseOffering'])),
            ('weekday', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('start_time', self.gf('django.db.models.fields.TimeField')()),
            ('end_time', self.gf('django.db.models.fields.TimeField')()),
            ('start_day', self.gf('django.db.models.fields.DateField')()),
            ('end_day', self.gf('django.db.models.fields.DateField')()),
            ('room', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('exam', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('meeting_type', self.gf('django.db.models.fields.CharField')(default='LEC', max_length=4)),
            ('labtut_section', self.gf('django.db.models.fields.CharField')(max_length=4, null=True, blank=True)),
        ))
        db.send_create_signal('coredata', ['MeetingTime'])

        # Adding model 'Unit'
        db.create_table('coredata_unit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(unique=True, max_length=4, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=60)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'], null=True, blank=True)),
            ('acad_org', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=10, unique=True, null=True, blank=True)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
        ))
        db.send_create_signal('coredata', ['Unit'])

        # Adding model 'Role'
        db.create_table('coredata_role', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
        ))
        db.send_create_signal('coredata', ['Role'])

        # Adding unique constraint on 'Role', fields ['person', 'role', 'unit']
        db.create_unique('coredata_role', ['person_id', 'role', 'unit_id'])

        # Adding model 'ComputingAccount'
        db.create_table('coredata_computingaccount', (
            ('emplid', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True, primary_key=True)),
            ('userid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=8, db_index=True)),
        ))
        db.send_create_signal('coredata', ['ComputingAccount'])


    def backwards(self, orm):
        # Removing unique constraint on 'Role', fields ['person', 'role', 'unit']
        db.delete_unique('coredata_role', ['person_id', 'role', 'unit_id'])

        # Removing unique constraint on 'CourseOffering', fields ['semester', 'class_nbr']
        db.delete_unique('coredata_courseoffering', ['semester_id', 'class_nbr'])

        # Removing unique constraint on 'CourseOffering', fields ['semester', 'crse_id', 'section']
        db.delete_unique('coredata_courseoffering', ['semester_id', 'crse_id', 'section'])

        # Removing unique constraint on 'CourseOffering', fields ['semester', 'subject', 'number', 'section']
        db.delete_unique('coredata_courseoffering', ['semester_id', 'subject', 'number', 'section'])

        # Removing unique constraint on 'Course', fields ['subject', 'number']
        db.delete_unique('coredata_course', ['subject', 'number'])

        # Removing unique constraint on 'SemesterWeek', fields ['semester', 'week']
        db.delete_unique('coredata_semesterweek', ['semester_id', 'week'])

        # Deleting model 'Person'
        db.delete_table('coredata_person')

        # Deleting model 'Semester'
        db.delete_table('coredata_semester')

        # Deleting model 'SemesterWeek'
        db.delete_table('coredata_semesterweek')

        # Deleting model 'Holiday'
        db.delete_table('coredata_holiday')

        # Deleting model 'Course'
        db.delete_table('coredata_course')

        # Deleting model 'CourseOffering'
        db.delete_table('coredata_courseoffering')

        # Deleting model 'Member'
        db.delete_table('coredata_member')

        # Deleting model 'MeetingTime'
        db.delete_table('coredata_meetingtime')

        # Deleting model 'Unit'
        db.delete_table('coredata_unit')

        # Deleting model 'Role'
        db.delete_table('coredata_role')

        # Deleting model 'ComputingAccount'
        db.delete_table('coredata_computingaccount')


    models = {
        'coredata.computingaccount': {
            'Meta': {'object_name': 'ComputingAccount'},
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'primary_key': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '8', 'db_index': 'True'})
        },
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
            'units': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'wait_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'coredata.holiday': {
            'Meta': {'ordering': "['date']", 'object_name': 'Holiday'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'holiday_type': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"})
        },
        'coredata.meetingtime': {
            'Meta': {'ordering': "['weekday']", 'object_name': 'MeetingTime'},
            'end_day': ('django.db.models.fields.DateField', [], {}),
            'end_time': ('django.db.models.fields.TimeField', [], {}),
            'exam': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'labtut_section': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'meeting_type': ('django.db.models.fields.CharField', [], {'default': "'LEC'", 'max_length': '4'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'room': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'start_day': ('django.db.models.fields.DateField', [], {}),
            'start_time': ('django.db.models.fields.TimeField', [], {}),
            'weekday': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
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
        'coredata.role': {
            'Meta': {'unique_together': "(('person', 'role', 'unit'),)", 'object_name': 'Role'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'coredata.semester': {
            'Meta': {'ordering': "['name']", 'object_name': 'Semester'},
            'end': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        'coredata.semesterweek': {
            'Meta': {'ordering': "['semester', 'week']", 'unique_together': "(('semester', 'week'),)", 'object_name': 'SemesterWeek'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'monday': ('django.db.models.fields.DateField', [], {}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'week': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
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
        }
    }

    complete_apps = ['coredata']