# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SubmittedWord'
        db.create_table('submission_submittedword', (
            ('submittedcomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmittedComponent'], unique=True, primary_key=True)),
            ('component', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submission.WordComponent'])),
            ('word', self.gf('django.db.models.fields.files.FileField')(max_length=500)),
        ))
        db.send_create_signal('submission', ['SubmittedWord'])

        # Adding model 'WordComponent'
        db.create_table('submission_wordcomponent', (
            ('submissioncomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmissionComponent'], unique=True, primary_key=True)),
            ('max_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=10000)),
        ))
        db.send_create_signal('submission', ['WordComponent'])

        # Adding field 'SubmissionComponent.specified_filename'
        db.add_column('submission_submissioncomponent', 'specified_filename', self.gf('django.db.models.fields.CharField')(default='', max_length=200), keep_default=False)


    def backwards(self, orm):
        
        # Deleting model 'SubmittedWord'
        db.delete_table('submission_submittedword')

        # Deleting model 'WordComponent'
        db.delete_table('submission_wordcomponent')

        # Deleting field 'SubmissionComponent.specified_filename'
        db.delete_column('submission_submissioncomponent', 'specified_filename')


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
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'member'", 'symmetrical': 'False', 'through': "orm['coredata.Member']", 'to': "orm['coredata.Person']"}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': '()', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'}),
            'wait_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'coredata.member': {
            'Meta': {'object_name': 'Member'},
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
        'coredata.semester': {
            'Meta': {'object_name': 'Semester'},
            'end': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        'grades.activity': {
            'Meta': {'object_name': 'Activity'},
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'due_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'db_index': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'percent': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '15', 'db_index': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': "('offering',)", 'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'})
        },
        'groups.group': {
            'Meta': {'unique_together': "(('name', 'courseoffering'),)", 'object_name': 'Group'},
            'courseoffering': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.CourseOffering']"}),
            'groupForSemester': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manager': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': "('courseoffering',)", 'db_index': 'True'})
        },
        'submission.archivecomponent': {
            'Meta': {'object_name': 'ArchiveComponent', '_ormbases': ['submission.SubmissionComponent']},
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.codecomponent': {
            'Meta': {'object_name': 'CodeComponent', '_ormbases': ['submission.SubmissionComponent']},
            'allowed': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2000'}),
            'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.groupsubmission': {
            'Meta': {'object_name': 'GroupSubmission', '_ormbases': ['submission.Submission']},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['groups.Group']"}),
            'submission_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.Submission']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.pdfcomponent': {
            'Meta': {'object_name': 'PDFComponent', '_ormbases': ['submission.SubmissionComponent']},
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5000'}),
            'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.studentsubmission': {
            'Meta': {'object_name': 'StudentSubmission', '_ormbases': ['submission.Submission']},
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"}),
            'submission_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.Submission']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submission': {
            'Meta': {'object_name': 'Submission'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.Activity']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']", 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'NEW'", 'max_length': '3'})
        },
        'submission.submissioncomponent': {
            'Meta': {'object_name': 'SubmissionComponent'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.Activity']"}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '50', 'unique': 'False', 'unique_with': "('activity',)", 'db_index': 'True'}),
            'specified_filename': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'submission.submittedarchive': {
            'Meta': {'object_name': 'SubmittedArchive', '_ormbases': ['submission.SubmittedComponent']},
            'archive': ('django.db.models.fields.files.FileField', [], {'max_length': '500'}),
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.ArchiveComponent']"}),
            'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submittedcode': {
            'Meta': {'object_name': 'SubmittedCode', '_ormbases': ['submission.SubmittedComponent']},
            'code': ('django.db.models.fields.files.FileField', [], {'max_length': '500'}),
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.CodeComponent']"}),
            'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submittedcomponent': {
            'Meta': {'object_name': 'SubmittedComponent'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.Submission']"}),
            'submit_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'submission.submittedpdf': {
            'Meta': {'object_name': 'SubmittedPDF', '_ormbases': ['submission.SubmittedComponent']},
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.PDFComponent']"}),
            'pdf': ('django.db.models.fields.files.FileField', [], {'max_length': '500'}),
            'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submittedurl': {
            'Meta': {'object_name': 'SubmittedURL', '_ormbases': ['submission.SubmittedComponent']},
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.URLComponent']"}),
            'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'submission.submittedword': {
            'Meta': {'object_name': 'SubmittedWord', '_ormbases': ['submission.SubmittedComponent']},
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.WordComponent']"}),
            'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'}),
            'word': ('django.db.models.fields.files.FileField', [], {'max_length': '500'})
        },
        'submission.urlcomponent': {
            'Meta': {'object_name': 'URLComponent', '_ormbases': ['submission.SubmissionComponent']},
            'check': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'prefix': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.wordcomponent': {
            'Meta': {'object_name': 'WordComponent', '_ormbases': ['submission.SubmissionComponent']},
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['submission']
