# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'SemesterConfig'
        db.create_table('ra_semesterconfig', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Semester'])),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
        ))
        db.send_create_signal('ra', ['SemesterConfig'])

        # Adding unique constraint on 'SemesterConfig', fields ['unit', 'semester']
        db.create_unique('ra_semesterconfig', ['unit_id', 'semester_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'SemesterConfig', fields ['unit', 'semester']
        db.delete_unique('ra_semesterconfig', ['unit_id', 'semester_id'])

        # Deleting model 'SemesterConfig'
        db.delete_table('ra_semesterconfig')


    models = {
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
        'grad.gradprogram': {
            'Meta': {'unique_together': "(('unit', 'label'),)", 'object_name': 'GradProgram'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'modified_by': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'grad.gradstudent': {
            'Meta': {'object_name': 'GradStudent'},
            'campus': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '5', 'blank': 'True'}),
            'comments': ('django.db.models.fields.TextField', [], {'max_length': '250', 'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'current_status': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'db_index': 'True'}),
            'end_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'grad_end_sem'", 'null': 'True', 'to': "orm['coredata.Semester']"}),
            'english_fluency': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_canadian': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'modified_by': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'mother_tongue': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'passport_issued_by': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradProgram']"}),
            'research_area': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'start_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'grad_start_sem'", 'null': 'True', 'to': "orm['coredata.Semester']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'grad.scholarship': {
            'Meta': {'object_name': 'Scholarship'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'scholarship_end'", 'to': "orm['coredata.Semester']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'scholarship_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.ScholarshipType']"}),
            'start_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'scholarship_start'", 'to': "orm['coredata.Semester']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradStudent']"})
        },
        'grad.scholarshiptype': {
            'Meta': {'object_name': 'ScholarshipType'},
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'eligible': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'ra.account': {
            'Meta': {'ordering': "['account_number']", 'object_name': 'Account'},
            'account_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'ra.project': {
            'Meta': {'ordering': "['project_number']", 'object_name': 'Project'},
            'fund_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'ra.raappointment': {
            'Meta': {'ordering': "['person', 'created_at']", 'object_name': 'RAAppointment'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ra.Account']"}),
            'biweekly_pay': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'dental_benefits': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'hiring_category': ('django.db.models.fields.CharField', [], {'default': "'S'", 'max_length': '60'}),
            'hiring_faculty': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ra_hiring_faculty'", 'to': "orm['coredata.Person']"}),
            'hourly_pay': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'hours': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lump_sum_pay': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'medical_benefits': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'offer_letter_text': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'pay_frequency': ('django.db.models.fields.CharField', [], {'default': "'B'", 'max_length': '60'}),
            'pay_periods': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '1'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ra_person'", 'to': "orm['coredata.Person']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ra.Project']"}),
            'reappointment': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'scholarship': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.Scholarship']", 'null': 'True', 'blank': 'True'}),
            'sin': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'ra.semesterconfig': {
            'Meta': {'unique_together': "(('unit', 'semester'),)", 'object_name': 'SemesterConfig'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        }
    }

    complete_apps = ['ra']