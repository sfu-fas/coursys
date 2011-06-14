# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'DisciplineCaseChair.instr_case'
        db.alter_column('discipline_disciplinecasechair', 'instr_case_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['discipline.DisciplineCaseInstr']))


    def backwards(self, orm):
        
        # Changing field 'DisciplineCaseChair.instr_case'
        db.alter_column('discipline_disciplinecasechair', 'instr_case_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['discipline.DisciplineCaseInstr'], null=True))


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
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
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': '()', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'wait_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'coredata.member': {
            'Meta': {'ordering': "['offering', 'person']", 'object_name': 'Member'},
            'added_reason': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'career': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'credits': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '3'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'person'", 'to': "orm['coredata.Person']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        'coredata.person': {
            'Meta': {'ordering': "['last_name', 'first_name', 'userid']", 'object_name': 'Person'},
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
        'discipline.caseattachment': {
            'Meta': {'unique_together': "(('case', 'name'),)", 'object_name': 'CaseAttachment'},
            'attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '500'}),
            'case': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['discipline.DisciplineCaseBase']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mediatype': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'discipline.disciplinecasebase': {
            'Meta': {'object_name': 'DisciplineCaseBase'},
            'contact_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'contact_email_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'contacted': ('django.db.models.fields.CharField', [], {'default': "'NONE'", 'max_length': '4'}),
            'facts': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['discipline.DisciplineGroup']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'letter_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'letter_review': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'letter_sent': ('django.db.models.fields.CharField', [], {'default': "'WAIT'", 'max_length': '4'}),
            'letter_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'meeting_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'meeting_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'meeting_summary': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'notes_public': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'penalty': ('django.db.models.fields.CharField', [], {'default': "'WAIT'", 'max_length': '4'}),
            'penalty_implemented': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'penalty_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'refer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'response': ('django.db.models.fields.CharField', [], {'default': "'WAIT'", 'max_length': '4'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': "('offering',)", 'db_index': 'True'})
        },
        'discipline.disciplinecasechair': {
            'Meta': {'object_name': 'DisciplineCaseChair', '_ormbases': ['discipline.DisciplineCaseBase']},
            'disciplinecasebase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['discipline.DisciplineCaseBase']", 'unique': 'True', 'primary_key': 'True'}),
            'instr_case': ('django.db.models.fields.related.ForeignKey', [], {'default': '0', 'to': "orm['discipline.DisciplineCaseInstr']"})
        },
        'discipline.disciplinecasechairnonstudent': {
            'Meta': {'object_name': 'DisciplineCaseChairNonStudent', '_ormbases': ['discipline.DisciplineCaseChair']},
            'disciplinecasechair_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['discipline.DisciplineCaseChair']", 'unique': 'True', 'primary_key': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'max_length': '9', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'blank': 'True'})
        },
        'discipline.disciplinecasechairstudent': {
            'Meta': {'object_name': 'DisciplineCaseChairStudent', '_ormbases': ['discipline.DisciplineCaseChair']},
            'disciplinecasechair_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['discipline.DisciplineCaseChair']", 'unique': 'True', 'primary_key': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"})
        },
        'discipline.disciplinecaseinstr': {
            'Meta': {'object_name': 'DisciplineCaseInstr', '_ormbases': ['discipline.DisciplineCaseBase']},
            'disciplinecasebase_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['discipline.DisciplineCaseBase']", 'unique': 'True', 'primary_key': 'True'})
        },
        'discipline.disciplinecaseinstrnonstudent': {
            'Meta': {'object_name': 'DisciplineCaseInstrNonStudent', '_ormbases': ['discipline.DisciplineCaseInstr']},
            'disciplinecaseinstr_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['discipline.DisciplineCaseInstr']", 'unique': 'True', 'primary_key': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'max_length': '9', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'blank': 'True'})
        },
        'discipline.disciplinecaseinstrstudent': {
            'Meta': {'object_name': 'DisciplineCaseInstrStudent', '_ormbases': ['discipline.DisciplineCaseInstr']},
            'disciplinecaseinstr_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['discipline.DisciplineCaseInstr']", 'unique': 'True', 'primary_key': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"})
        },
        'discipline.disciplinegroup': {
            'Meta': {'unique_together': "(('name', 'offering'),)", 'object_name': 'DisciplineGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': "('offering',)", 'db_index': 'True'})
        },
        'discipline.disciplinetemplate': {
            'Meta': {'ordering': "('field', 'label')", 'unique_together': "(('field', 'label'),)", 'object_name': 'DisciplineTemplate'},
            'field': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'discipline.relatedobject': {
            'Meta': {'object_name': 'RelatedObject'},
            'case': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['discipline.DisciplineCaseBase']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {})
        }
    }

    complete_apps = ['discipline']
