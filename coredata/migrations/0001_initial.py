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
            ('config', self.gf('jsonfield.JSONField')(default={})),
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
            ('graded', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('crse_id', self.gf('django.db.models.fields.PositiveSmallIntegerField')(db_index=True)),
            ('class_nbr', self.gf('django.db.models.fields.PositiveSmallIntegerField')(db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('campus', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('enrl_cap', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('enrl_tot', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('wait_tot', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('config', self.gf('jsonfield.JSONField')(default={})),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=(), db_index=True)),
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
            ('config', self.gf('jsonfield.JSONField')(default={})),
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

        # Adding model 'Role'
        db.create_table('coredata_role', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('department', self.gf('django.db.models.fields.CharField')(max_length=4)),
        ))
        db.send_create_signal('coredata', ['Role'])

        # Adding unique constraint on 'Role', fields ['person', 'role']
        db.create_unique('coredata_role', ['person_id', 'role'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Role', fields ['person', 'role']
        db.delete_unique('coredata_role', ['person_id', 'role'])

        # Removing unique constraint on 'CourseOffering', fields ['semester', 'class_nbr']
        db.delete_unique('coredata_courseoffering', ['semester_id', 'class_nbr'])

        # Removing unique constraint on 'CourseOffering', fields ['semester', 'crse_id', 'section']
        db.delete_unique('coredata_courseoffering', ['semester_id', 'crse_id', 'section'])

        # Removing unique constraint on 'CourseOffering', fields ['semester', 'subject', 'number', 'section']
        db.delete_unique('coredata_courseoffering', ['semester_id', 'subject', 'number', 'section'])

        # Removing unique constraint on 'SemesterWeek', fields ['semester', 'week']
        db.delete_unique('coredata_semesterweek', ['semester_id', 'week'])

        # Deleting model 'Person'
        db.delete_table('coredata_person')

        # Deleting model 'Semester'
        db.delete_table('coredata_semester')

        # Deleting model 'SemesterWeek'
        db.delete_table('coredata_semesterweek')

        # Deleting model 'CourseOffering'
        db.delete_table('coredata_courseoffering')

        # Deleting model 'Member'
        db.delete_table('coredata_member')

        # Deleting model 'MeetingTime'
        db.delete_table('coredata_meetingtime')

        # Deleting model 'Role'
        db.delete_table('coredata_role')


    models = {
        'coredata.courseoffering': {
            'Meta': {'ordering': "['-semester', 'subject', 'number', 'section']", 'unique_together': "(('semester', 'subject', 'number', 'section'), ('semester', 'crse_id', 'section'), ('semester', 'class_nbr'))", 'object_name': 'CourseOffering'},
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'class_nbr': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'crse_id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'}),
            'enrl_cap': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'enrl_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'graded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'member'", 'symmetrical': 'False', 'through': "orm['coredata.Member']", 'to': "orm['coredata.Person']"}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'wait_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
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
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'credits': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '3'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'labtut_section': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'person'", 'to': "orm['coredata.Person']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
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
        'coredata.role': {
            'Meta': {'unique_together': "(('person', 'role'),)", 'object_name': 'Role'},
            'department': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '4'})
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
        }
    }

    complete_apps = ['coredata']
