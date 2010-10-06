# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SubmissionComponent'
        db.create_table('submission_submissioncomponent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grades.Activity'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=1000, null=True, blank=True)),
            ('position', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(max_length=50, unique=False, unique_with=('activity',), db_index=True)),
            ('deleted', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
        ))
        db.send_create_signal('submission', ['SubmissionComponent'])

        # Adding model 'Submission'
        db.create_table('submission_submission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grades.Activity'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Member'], null=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='NEW', max_length=3)),
        ))
        db.send_create_signal('submission', ['Submission'])

        # Adding model 'StudentSubmission'
        db.create_table('submission_studentsubmission', (
            ('submission_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.Submission'], unique=True, primary_key=True)),
            ('member', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Member'])),
        ))
        db.send_create_signal('submission', ['StudentSubmission'])

        # Adding model 'GroupSubmission'
        db.create_table('submission_groupsubmission', (
            ('submission_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.Submission'], unique=True, primary_key=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['groups.Group'])),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Member'])),
        ))
        db.send_create_signal('submission', ['GroupSubmission'])

        # Adding model 'SubmittedComponent'
        db.create_table('submission_submittedcomponent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submission.Submission'])),
            ('submit_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('submission', ['SubmittedComponent'])

        # Adding model 'URLComponent'
        db.create_table('submission_urlcomponent', (
            ('submissioncomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmissionComponent'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('submission', ['URLComponent'])

        # Adding model 'SubmittedURL'
        db.create_table('submission_submittedurl', (
            ('submittedcomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmittedComponent'], unique=True, primary_key=True)),
            ('component', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submission.URLComponent'])),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=500)),
        ))
        db.send_create_signal('submission', ['SubmittedURL'])

        # Adding model 'ArchiveComponent'
        db.create_table('submission_archivecomponent', (
            ('submissioncomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmissionComponent'], unique=True, primary_key=True)),
            ('max_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=10000)),
        ))
        db.send_create_signal('submission', ['ArchiveComponent'])

        # Adding model 'SubmittedArchive'
        db.create_table('submission_submittedarchive', (
            ('submittedcomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmittedComponent'], unique=True, primary_key=True)),
            ('component', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submission.ArchiveComponent'])),
            ('archive', self.gf('django.db.models.fields.files.FileField')(max_length=500)),
        ))
        db.send_create_signal('submission', ['SubmittedArchive'])

        # Adding model 'PDFComponent'
        db.create_table('submission_pdfcomponent', (
            ('submissioncomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmissionComponent'], unique=True, primary_key=True)),
            ('max_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=5000)),
        ))
        db.send_create_signal('submission', ['PDFComponent'])

        # Adding model 'SubmittedPDF'
        db.create_table('submission_submittedpdf', (
            ('submittedcomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmittedComponent'], unique=True, primary_key=True)),
            ('component', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submission.PDFComponent'])),
            ('pdf', self.gf('django.db.models.fields.files.FileField')(max_length=500)),
        ))
        db.send_create_signal('submission', ['SubmittedPDF'])

        # Adding model 'CodeComponent'
        db.create_table('submission_codecomponent', (
            ('submissioncomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmissionComponent'], unique=True, primary_key=True)),
            ('max_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=2000)),
            ('allowed', self.gf('django.db.models.fields.CharField')(max_length=500)),
        ))
        db.send_create_signal('submission', ['CodeComponent'])

        # Adding model 'SubmittedCode'
        db.create_table('submission_submittedcode', (
            ('submittedcomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmittedComponent'], unique=True, primary_key=True)),
            ('component', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submission.CodeComponent'])),
            ('code', self.gf('django.db.models.fields.files.FileField')(max_length=500)),
        ))
        db.send_create_signal('submission', ['SubmittedCode'])


    def backwards(self, orm):
        
        # Deleting model 'SubmissionComponent'
        db.delete_table('submission_submissioncomponent')

        # Deleting model 'Submission'
        db.delete_table('submission_submission')

        # Deleting model 'StudentSubmission'
        db.delete_table('submission_studentsubmission')

        # Deleting model 'GroupSubmission'
        db.delete_table('submission_groupsubmission')

        # Deleting model 'SubmittedComponent'
        db.delete_table('submission_submittedcomponent')

        # Deleting model 'URLComponent'
        db.delete_table('submission_urlcomponent')

        # Deleting model 'SubmittedURL'
        db.delete_table('submission_submittedurl')

        # Deleting model 'ArchiveComponent'
        db.delete_table('submission_archivecomponent')

        # Deleting model 'SubmittedArchive'
        db.delete_table('submission_submittedarchive')

        # Deleting model 'PDFComponent'
        db.delete_table('submission_pdfcomponent')

        # Deleting model 'SubmittedPDF'
        db.delete_table('submission_submittedpdf')

        # Deleting model 'CodeComponent'
        db.delete_table('submission_codecomponent')

        # Deleting model 'SubmittedCode'
        db.delete_table('submission_submittedcode')


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
            'status': ('django.db.models.fields.CharField', [], {'max_length': '4'})
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
        'submission.urlcomponent': {
            'Meta': {'object_name': 'URLComponent', '_ormbases': ['submission.SubmissionComponent']},
            'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['submission']
