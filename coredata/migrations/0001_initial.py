# encoding: utf-8
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
            ('pref_first_name', self.gf('django.db.models.fields.CharField')(max_length=32)),
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

        # Adding model 'CourseOffering'
        db.create_table('coredata_courseoffering', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=4, db_index=True)),
            ('number', self.gf('django.db.models.fields.CharField')(max_length=4, db_index=True)),
            ('section', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Semester'])),
            ('component', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('graded', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('crse_id', self.gf('django.db.models.fields.PositiveSmallIntegerField')(db_index=True)),
            ('class_nbr', self.gf('django.db.models.fields.PositiveSmallIntegerField')(db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('campus', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('enrl_cap', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('enrl_tot', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('wait_tot', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(max_length=50, unique=False, unique_with=(), db_index=True)),
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
        ))
        db.send_create_signal('coredata', ['Member'])

        # Adding unique constraint on 'Member', fields ['person', 'offering', 'role']
        db.create_unique('coredata_member', ['person_id', 'offering_id', 'role'])

        # Adding model 'MeetingTime'
        db.create_table('coredata_meetingtime', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('offering', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.CourseOffering'])),
            ('weekday', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('start_time', self.gf('django.db.models.fields.TimeField')()),
            ('end_time', self.gf('django.db.models.fields.TimeField')()),
            ('timezone', self.gf('timezones.fields.TimeZoneField')(default='America/Vancouver', max_length=100)),
            ('room', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('coredata', ['MeetingTime'])

        # Adding model 'Role'
        db.create_table('coredata_role', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=4)),
        ))
        db.send_create_signal('coredata', ['Role'])

        # Adding unique constraint on 'Role', fields ['person', 'role']
        db.create_unique('coredata_role', ['person_id', 'role'])


    def backwards(self, orm):
        
        # Deleting model 'Person'
        db.delete_table('coredata_person')

        # Deleting model 'Semester'
        db.delete_table('coredata_semester')

        # Deleting model 'SemesterWeek'
        db.delete_table('coredata_semesterweek')

        # Removing unique constraint on 'SemesterWeek', fields ['semester', 'week']
        db.delete_unique('coredata_semesterweek', ['semester_id', 'week'])

        # Deleting model 'CourseOffering'
        db.delete_table('coredata_courseoffering')

        # Removing unique constraint on 'CourseOffering', fields ['semester', 'subject', 'number', 'section']
        db.delete_unique('coredata_courseoffering', ['semester_id', 'subject', 'number', 'section'])

        # Removing unique constraint on 'CourseOffering', fields ['semester', 'crse_id', 'section']
        db.delete_unique('coredata_courseoffering', ['semester_id', 'crse_id', 'section'])

        # Removing unique constraint on 'CourseOffering', fields ['semester', 'class_nbr']
        db.delete_unique('coredata_courseoffering', ['semester_id', 'class_nbr'])

        # Deleting model 'Member'
        db.delete_table('coredata_member')

        # Removing unique constraint on 'Member', fields ['person', 'offering', 'role']
        db.delete_unique('coredata_member', ['person_id', 'offering_id', 'role'])

        # Deleting model 'MeetingTime'
        db.delete_table('coredata_meetingtime')

        # Deleting model 'Role'
        db.delete_table('coredata_role')

        # Removing unique constraint on 'Role', fields ['person', 'role']
        db.delete_unique('coredata_role', ['person_id', 'role'])


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
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'member'", 'through': "'Member'", 'to': "orm['coredata.Person']"}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': '()', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'wait_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'coredata.meetingtime': {
            'Meta': {'object_name': 'MeetingTime'},
            'end_time': ('django.db.models.fields.TimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'room': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'start_time': ('django.db.models.fields.TimeField', [], {}),
            'timezone': ('timezones.fields.TimeZoneField', [], {'default': "'America/Vancouver'", 'max_length': '100'}),
            'weekday': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'coredata.member': {
            'Meta': {'unique_together': "(('person', 'offering', 'role'),)", 'object_name': 'Member'},
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
        'coredata.role': {
            'Meta': {'unique_together': "(('person', 'role'),)", 'object_name': 'Role'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        'coredata.semester': {
            'Meta': {'object_name': 'Semester'},
            'end': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        'coredata.semesterweek': {
            'Meta': {'unique_together': "(('semester', 'week'),)", 'object_name': 'SemesterWeek'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'monday': ('django.db.models.fields.DateField', [], {}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'week': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        }
    }

    complete_apps = ['coredata']
