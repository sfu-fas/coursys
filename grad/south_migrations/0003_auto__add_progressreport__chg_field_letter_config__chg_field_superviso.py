# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ProgressReport'
        db.create_table(u'grad_progressreport', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradStudent'])),
            ('result', self.gf('django.db.models.fields.CharField')(max_length=5, db_index=True)),
            ('removed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('config', self.gf('courselib.json_fields.JSONField')(default={})),
            ('comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'grad', ['ProgressReport'])

        # Changing field 'Letter.config'
        db.alter_column(u'grad_letter', 'config', self.gf('courselib.json_fields.JSONField')())

        # Changing field 'Supervisor.config'
        db.alter_column(u'grad_supervisor', 'config', self.gf('courselib.json_fields.JSONField')())

        # Changing field 'GradProgram.slug'
        db.alter_column(u'grad_gradprogram', 'slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=('unit',), max_length=50, populate_from=None))

        # Changing field 'SavedSearch.config'
        db.alter_column(u'grad_savedsearch', 'config', self.gf('courselib.json_fields.JSONField')())

        # Changing field 'GradStudent.config'
        db.alter_column(u'grad_gradstudent', 'config', self.gf('courselib.json_fields.JSONField')())

    def backwards(self, orm):
        # Deleting model 'ProgressReport'
        db.delete_table(u'grad_progressreport')


        # Changing field 'Letter.config'
        db.alter_column(u'grad_letter', 'config', self.gf('jsonfield.fields.JSONField')())

        # Changing field 'Supervisor.config'
        db.alter_column(u'grad_supervisor', 'config', self.gf('jsonfield.fields.JSONField')())

        # Changing field 'GradProgram.slug'
        db.alter_column(u'grad_gradprogram', 'slug', self.gf('autoslug.fields.AutoSlugField')(max_length=50, unique_with=(), populate_from=None))

        # Changing field 'SavedSearch.config'
        db.alter_column(u'grad_savedsearch', 'config', self.gf('jsonfield.fields.JSONField')())

        # Changing field 'GradStudent.config'
        db.alter_column(u'grad_gradstudent', 'config', self.gf('jsonfield.fields.JSONField')())

    models = {
        u'coredata.person': {
            'Meta': {'ordering': "['last_name', 'first_name', 'userid']", 'object_name': 'Person'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'db_index': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '8', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'coredata.semester': {
            'Meta': {'ordering': "['name']", 'object_name': 'Semester'},
            'end': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        u'coredata.unit': {
            'Meta': {'ordering': "['label']", 'object_name': 'Unit'},
            'acad_org': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        u'grad.completedrequirement': {
            'Meta': {'object_name': 'CompletedRequirement'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'requirement': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradRequirement']"}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Semester']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'grad.financialcomment': {
            'Meta': {'object_name': 'FinancialComment'},
            'comment': ('django.db.models.fields.TextField', [], {}),
            'comment_type': ('django.db.models.fields.CharField', [], {'default': "'OTH'", 'max_length': '3'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['coredata.Semester']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"})
        },
        u'grad.gradflag': {
            'Meta': {'unique_together': "(('unit', 'label'),)", 'object_name': 'GradFlag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'grad.gradflagvalue': {
            'Meta': {'object_name': 'GradFlagValue'},
            'flag': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradFlag']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"}),
            'value': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'grad.gradprogram': {
            'Meta': {'unique_together': "(('unit', 'label'),)", 'object_name': 'GradProgram'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'modified_by': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('unit',)", 'max_length': '50', 'populate_from': 'None'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'grad.gradprogramhistory': {
            'Meta': {'ordering': "('-starting',)", 'object_name': 'GradProgramHistory'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradProgram']"}),
            'start_semester': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Semester']"}),
            'starting': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"})
        },
        u'grad.gradrequirement': {
            'Meta': {'unique_together': "(('program', 'description'),)", 'object_name': 'GradRequirement'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradProgram']"}),
            'series': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'grad.gradstatus': {
            'Meta': {'object_name': 'GradStatus'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'end_semester'", 'null': 'True', 'to': u"orm['coredata.Semester']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'start': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'start_semester'", 'to': u"orm['coredata.Semester']"}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'grad.gradstudent': {
            'Meta': {'object_name': 'GradStudent'},
            'campus': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '5', 'blank': 'True'}),
            'comments': ('django.db.models.fields.TextField', [], {'max_length': '250', 'blank': 'True'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'current_status': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'db_index': 'True'}),
            'end_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'grad_end_sem'", 'null': 'True', 'to': u"orm['coredata.Semester']"}),
            'english_fluency': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_canadian': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'modified_by': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'mother_tongue': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'passport_issued_by': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']"}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradProgram']"}),
            'research_area': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'start_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'grad_start_sem'", 'null': 'True', 'to': u"orm['coredata.Semester']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'grad.letter': {
            'Meta': {'object_name': 'Letter'},
            'closing': ('django.db.models.fields.CharField', [], {'default': "'Sincerely'", 'max_length': '100'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'from_lines': ('django.db.models.fields.TextField', [], {}),
            'from_person': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.LetterTemplate']"}),
            'to_lines': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'grad.lettertemplate': {
            'Meta': {'unique_together': "(('unit', 'label'),)", 'object_name': 'LetterTemplate'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'grad.otherfunding': {
            'Meta': {'object_name': 'OtherFunding'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'eligible': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'other_funding'", 'to': u"orm['coredata.Semester']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"})
        },
        u'grad.progressreport': {
            'Meta': {'object_name': 'ProgressReport'},
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'result': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"})
        },
        u'grad.promise': {
            'Meta': {'object_name': 'Promise'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'promise_end'", 'to': u"orm['coredata.Semester']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'start_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'promise_start'", 'to': u"orm['coredata.Semester']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"})
        },
        u'grad.savedsearch': {
            'Meta': {'object_name': 'SavedSearch'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']", 'null': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        u'grad.scholarship': {
            'Meta': {'object_name': 'Scholarship'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'scholarship_end'", 'to': u"orm['coredata.Semester']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'scholarship_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.ScholarshipType']"}),
            'start_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'scholarship_start'", 'to': u"orm['coredata.Semester']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"})
        },
        u'grad.scholarshiptype': {
            'Meta': {'object_name': 'ScholarshipType'},
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'eligible': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'grad.supervisor': {
            'Meta': {'object_name': 'Supervisor'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'external': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_by': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grad.GradStudent']"}),
            'supervisor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']", 'null': 'True', 'blank': 'True'}),
            'supervisor_type': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['grad']
