# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    depends_on = (
        ("ra", "0001_initial"),
    )

    def forwards(self, orm):
        
        # Adding model 'TUG'
        db.create_table('ta_tug', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('member', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Member'], unique=True)),
            ('base_units', self.gf('django.db.models.fields.DecimalField')(max_digits=4, decimal_places=2)),
            ('last_update', self.gf('django.db.models.fields.DateField')(auto_now=True, blank=True)),
            ('config', self.gf('jsonfield.JSONField')(default={})),
        ))
        db.send_create_signal('ta', ['TUG'])

        # Adding model 'TAPosting'
        db.create_table('ta_taposting', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Semester'])),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('opens', self.gf('django.db.models.fields.DateField')()),
            ('closes', self.gf('django.db.models.fields.DateField')()),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=(), db_index=True)),
            ('config', self.gf('jsonfield.JSONField')(default={})),
        ))
        db.send_create_signal('ta', ['TAPosting'])

        # Adding unique constraint on 'TAPosting', fields ['unit', 'semester']
        db.create_unique('ta_taposting', ['unit_id', 'semester_id'])

        # Adding model 'Skill'
        db.create_table('ta_skill', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('posting', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ta.TAPosting'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('position', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('ta', ['Skill'])

        # Adding unique constraint on 'Skill', fields ['posting', 'position']
        db.create_unique('ta_skill', ['posting_id', 'position'])

        # Adding model 'TAApplication'
        db.create_table('ta_taapplication', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('posting', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ta.TAPosting'])),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('base_units', self.gf('django.db.models.fields.DecimalField')(default=5, max_digits=4, decimal_places=2)),
            ('sin', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('experience', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('course_load', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('other_support', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('rank', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('late', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('admin_created', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('ta', ['TAApplication'])

        # Adding unique constraint on 'TAApplication', fields ['person', 'posting']
        db.create_unique('ta_taapplication', ['person_id', 'posting_id'])

        # Adding model 'CampusPreference'
        db.create_table('ta_campuspreference', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ta.TAApplication'])),
            ('campus', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('pref', self.gf('django.db.models.fields.CharField')(max_length=3)),
        ))
        db.send_create_signal('ta', ['CampusPreference'])

        # Adding model 'SkillLevel'
        db.create_table('ta_skilllevel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('skill', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ta.Skill'])),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ta.TAApplication'])),
            ('level', self.gf('django.db.models.fields.CharField')(max_length=4)),
        ))
        db.send_create_signal('ta', ['SkillLevel'])

        # Adding model 'TAContract'
        db.create_table('ta_tacontract', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('posting', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ta.TAPosting'])),
            ('application', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ta.TAApplication'])),
            ('sin', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('pay_start', self.gf('django.db.models.fields.DateField')()),
            ('pay_end', self.gf('django.db.models.fields.DateField')()),
            ('appt_category', self.gf('django.db.models.fields.CharField')(default='GTA1', max_length=4)),
            ('position_number', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ra.Account'])),
            ('appt', self.gf('django.db.models.fields.CharField')(default='INIT', max_length=4)),
            ('pay_per_bu', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('scholarship_per_bu', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('appt_cond', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('appt_tssu', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('deadline', self.gf('django.db.models.fields.DateField')()),
            ('status', self.gf('django.db.models.fields.CharField')(default='NEW', max_length=3)),
            ('remarks', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('created_by', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('ta', ['TAContract'])

        # Adding unique constraint on 'TAContract', fields ['posting', 'application']
        db.create_unique('ta_tacontract', ['posting_id', 'application_id'])

        # Adding model 'TACourse'
        db.create_table('ta_tacourse', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.CourseOffering'])),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ta.TAContract'])),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('bu', self.gf('django.db.models.fields.DecimalField')(max_digits=4, decimal_places=2)),
        ))
        db.send_create_signal('ta', ['TACourse'])

        # Adding unique constraint on 'TACourse', fields ['contract', 'course']
        db.create_unique('ta_tacourse', ['contract_id', 'course_id'])

        # Adding model 'CoursePreference'
        db.create_table('ta_coursepreference', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ta.TAApplication'])),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Course'])),
            ('taken', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('exper', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('rank', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('ta', ['CoursePreference'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'TACourse', fields ['contract', 'course']
        db.delete_unique('ta_tacourse', ['contract_id', 'course_id'])

        # Removing unique constraint on 'TAContract', fields ['posting', 'application']
        db.delete_unique('ta_tacontract', ['posting_id', 'application_id'])

        # Removing unique constraint on 'TAApplication', fields ['person', 'posting']
        db.delete_unique('ta_taapplication', ['person_id', 'posting_id'])

        # Removing unique constraint on 'Skill', fields ['posting', 'position']
        db.delete_unique('ta_skill', ['posting_id', 'position'])

        # Removing unique constraint on 'TAPosting', fields ['unit', 'semester']
        db.delete_unique('ta_taposting', ['unit_id', 'semester_id'])

        # Deleting model 'TUG'
        db.delete_table('ta_tug')

        # Deleting model 'TAPosting'
        db.delete_table('ta_taposting')

        # Deleting model 'Skill'
        db.delete_table('ta_skill')

        # Deleting model 'TAApplication'
        db.delete_table('ta_taapplication')

        # Deleting model 'CampusPreference'
        db.delete_table('ta_campuspreference')

        # Deleting model 'SkillLevel'
        db.delete_table('ta_skilllevel')

        # Deleting model 'TAContract'
        db.delete_table('ta_tacontract')

        # Deleting model 'TACourse'
        db.delete_table('ta_tacourse')

        # Deleting model 'CoursePreference'
        db.delete_table('ta_coursepreference')


    models = {
        'coredata.course': {
            'Meta': {'ordering': "('subject', 'number')", 'unique_together': "(('subject', 'number'),)", 'object_name': 'Course'},
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'coredata.courseoffering': {
            'Meta': {'ordering': "['-semester', 'subject', 'number', 'section']", 'unique_together': "(('semester', 'subject', 'number', 'section'), ('semester', 'crse_id', 'section'), ('semester', 'class_nbr'))", 'object_name': 'CourseOffering'},
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'class_nbr': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Course']"}),
            'crse_id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'db_index': 'True'}),
            'enrl_cap': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'enrl_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'graded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'member'", 'symmetrical': 'False', 'through': "orm['coredata.Member']", 'to': "orm['coredata.Person']"}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']", 'null': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'wait_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
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
            'official_grade': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
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
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
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
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None', 'db_index': 'True'})
        },
        'ra.account': {
            'Meta': {'object_name': 'Account'},
            'account_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'ta.campuspreference': {
            'Meta': {'object_name': 'CampusPreference'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ta.TAApplication']"}),
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pref': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'ta.coursepreference': {
            'Meta': {'object_name': 'CoursePreference'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ta.TAApplication']"}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Course']"}),
            'exper': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rank': ('django.db.models.fields.IntegerField', [], {}),
            'taken': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'ta.skill': {
            'Meta': {'ordering': "['position']", 'unique_together': "(('posting', 'position'),)", 'object_name': 'Skill'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'position': ('django.db.models.fields.IntegerField', [], {}),
            'posting': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ta.TAPosting']"})
        },
        'ta.skilllevel': {
            'Meta': {'object_name': 'SkillLevel'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ta.TAApplication']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'skill': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ta.Skill']"})
        },
        'ta.taapplication': {
            'Meta': {'unique_together': "(('person', 'posting'),)", 'object_name': 'TAApplication'},
            'admin_created': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'base_units': ('django.db.models.fields.DecimalField', [], {'default': '5', 'max_digits': '4', 'decimal_places': '2'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'course_load': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'experience': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'late': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'other_support': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'posting': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ta.TAPosting']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'sin': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'ta.tacontract': {
            'Meta': {'unique_together': "(('posting', 'application'),)", 'object_name': 'TAContract'},
            'application': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ta.TAApplication']"}),
            'appt': ('django.db.models.fields.CharField', [], {'default': "'INIT'", 'max_length': '4'}),
            'appt_category': ('django.db.models.fields.CharField', [], {'default': "'GTA1'", 'max_length': '4'}),
            'appt_cond': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'appt_tssu': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'deadline': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pay_end': ('django.db.models.fields.DateField', [], {}),
            'pay_per_bu': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'pay_start': ('django.db.models.fields.DateField', [], {}),
            'position_number': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ra.Account']"}),
            'posting': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ta.TAPosting']"}),
            'remarks': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'scholarship_per_bu': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'sin': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'NEW'", 'max_length': '3'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'ta.tacourse': {
            'Meta': {'unique_together': "(('contract', 'course'),)", 'object_name': 'TACourse'},
            'bu': ('django.db.models.fields.DecimalField', [], {'max_digits': '4', 'decimal_places': '2'}),
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ta.TAContract']"}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'ta.taposting': {
            'Meta': {'unique_together': "(('unit', 'semester'),)", 'object_name': 'TAPosting'},
            'closes': ('django.db.models.fields.DateField', [], {}),
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'opens': ('django.db.models.fields.DateField', [], {}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()', 'db_index': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'ta.tug': {
            'Meta': {'object_name': 'TUG'},
            'base_units': ('django.db.models.fields.DecimalField', [], {'max_digits': '4', 'decimal_places': '2'}),
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_update': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'blank': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']", 'unique': 'True'})
        }
    }

    complete_apps = ['ta']
