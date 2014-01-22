# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CodefileComponent'
        db.create_table(u'submission_codefilecomponent', (
            (u'submissioncomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmissionComponent'], unique=True, primary_key=True)),
            ('max_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=2000)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('filename_type', self.gf('django.db.models.fields.CharField')(max_length=3)),
        ))
        db.send_create_signal('submission', ['CodefileComponent'])

        # Adding model 'SubmittedCodefile'
        db.create_table(u'submission_submittedcodefile', (
            (u'submittedcomponent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['submission.SubmittedComponent'], unique=True, primary_key=True)),
            ('component', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['submission.CodefileComponent'])),
            ('code', self.gf('django.db.models.fields.files.FileField')(max_length=500)),
        ))
        db.send_create_signal('submission', ['SubmittedCodefile'])


        # Changing field 'SubmissionComponent.slug'
        db.alter_column(u'submission_submissioncomponent', 'slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=('activity',), max_length=50, populate_from=None))

    def backwards(self, orm):
        # Deleting model 'CodefileComponent'
        db.delete_table(u'submission_codefilecomponent')

        # Deleting model 'SubmittedCodefile'
        db.delete_table(u'submission_submittedcodefile')


        # Changing field 'SubmissionComponent.slug'
        db.alter_column(u'submission_submissioncomponent', 'slug', self.gf('autoslug.fields.AutoSlugField')(max_length=50, unique_with=(), populate_from=None))

    models = {
        u'coredata.course': {
            'Meta': {'ordering': "('subject', 'number')", 'unique_together': "(('subject', 'number'),)", 'object_name': 'Course'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        u'coredata.courseoffering': {
            'Meta': {'ordering': "['-semester', 'subject', 'number', 'section']", 'unique_together': "(('semester', 'subject', 'number', 'section'), ('semester', 'crse_id', 'section'), ('semester', 'class_nbr'))", 'object_name': 'CourseOffering'},
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'class_nbr': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'component': ('django.db.models.fields.CharField', [], {'max_length': '3', 'db_index': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Course']"}),
            'crse_id': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'enrl_cap': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'enrl_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'flags': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            'graded': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instr_mode': ('django.db.models.fields.CharField', [], {'default': "'P'", 'max_length': '2', 'db_index': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'member'", 'symmetrical': 'False', 'through': u"orm['coredata.Member']", 'to': u"orm['coredata.Person']"}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']", 'null': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Semester']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '30', 'db_index': 'True'}),
            'units': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'wait_tot': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        u'coredata.member': {
            'Meta': {'ordering': "['offering', 'person']", 'object_name': 'Member'},
            'added_reason': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'career': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'credits': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'labtut_section': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.CourseOffering']"}),
            'official_grade': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'person'", 'to': u"orm['coredata.Person']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        u'coredata.person': {
            'Meta': {'ordering': "['last_name', 'first_name', 'userid']", 'object_name': 'Person'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'db_index': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '8', 'unique': 'True', 'null': 'True', 'db_index': 'True'})
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
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        u'grades.activity': {
            'Meta': {'ordering': "['deleted', 'position']", 'unique_together': "(('offering', 'slug'),)", 'object_name': 'Activity'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'due_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'db_index': 'True'}),
            'offering': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.CourseOffering']"}),
            'percent': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '15', 'db_index': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('offering',)", 'max_length': '50', 'populate_from': 'None'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        u'groups.group': {
            'Meta': {'ordering': "['name']", 'unique_together': "(('name', 'courseoffering'), ('slug', 'courseoffering'), ('svn_slug', 'courseoffering'))", 'object_name': 'Group'},
            'courseoffering': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.CourseOffering']"}),
            'groupForSemester': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manager': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Member']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('courseoffering',)", 'max_length': '50', 'populate_from': 'None'}),
            'svn_slug': ('autoslug.fields.AutoSlugField', [], {'max_length': '17', 'unique_with': "('courseoffering',)", 'null': 'True', 'populate_from': "'slug'"})
        },
        'submission.archivecomponent': {
            'Meta': {'ordering': "['position']", 'object_name': 'ArchiveComponent', '_ormbases': ['submission.SubmissionComponent']},
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            u'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.codecomponent': {
            'Meta': {'ordering': "['position']", 'object_name': 'CodeComponent', '_ormbases': ['submission.SubmissionComponent']},
            'allowed': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2000'}),
            u'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.codefilecomponent': {
            'Meta': {'ordering': "['position']", 'object_name': 'CodefileComponent', '_ormbases': ['submission.SubmissionComponent']},
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'filename_type': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2000'}),
            u'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.groupsubmission': {
            'Meta': {'ordering': "['-created_at']", 'object_name': 'GroupSubmission', '_ormbases': ['submission.Submission']},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Member']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['groups.Group']"}),
            u'submission_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.Submission']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.imagecomponent': {
            'Meta': {'ordering': "['position']", 'object_name': 'ImageComponent', '_ormbases': ['submission.SubmissionComponent']},
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1000'}),
            u'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.officecomponent': {
            'Meta': {'ordering': "['position']", 'object_name': 'OfficeComponent', '_ormbases': ['submission.SubmissionComponent']},
            'allowed': ('submission.models.office.JSONFieldFlexible', [], {'max_length': '500'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            u'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.pdfcomponent': {
            'Meta': {'ordering': "['position']", 'object_name': 'PDFComponent', '_ormbases': ['submission.SubmissionComponent']},
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5000'}),
            u'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.studentsubmission': {
            'Meta': {'ordering': "['-created_at']", 'object_name': 'StudentSubmission', '_ormbases': ['submission.Submission']},
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Member']"}),
            u'submission_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.Submission']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submission': {
            'Meta': {'ordering': "['-created_at']", 'object_name': 'Submission'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grades.Activity']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Member']", 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'NEW'", 'max_length': '3'})
        },
        'submission.submissioncomponent': {
            'Meta': {'ordering': "['position']", 'object_name': 'SubmissionComponent'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['grades.Activity']"}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('activity',)", 'max_length': '50', 'populate_from': 'None'}),
            'specified_filename': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'submission.submittedarchive': {
            'Meta': {'ordering': "['submit_time']", 'object_name': 'SubmittedArchive', '_ormbases': ['submission.SubmittedComponent']},
            'archive': ('django.db.models.fields.files.FileField', [], {'max_length': '500'}),
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.ArchiveComponent']"}),
            u'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submittedcode': {
            'Meta': {'ordering': "['submit_time']", 'object_name': 'SubmittedCode', '_ormbases': ['submission.SubmittedComponent']},
            'code': ('django.db.models.fields.files.FileField', [], {'max_length': '500'}),
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.CodeComponent']"}),
            u'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submittedcodefile': {
            'Meta': {'ordering': "['submit_time']", 'object_name': 'SubmittedCodefile', '_ormbases': ['submission.SubmittedComponent']},
            'code': ('django.db.models.fields.files.FileField', [], {'max_length': '500'}),
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.CodefileComponent']"}),
            u'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submittedcomponent': {
            'Meta': {'ordering': "['submit_time']", 'object_name': 'SubmittedComponent'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.Submission']"}),
            'submit_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'submission.submittedimage': {
            'Meta': {'ordering': "['submit_time']", 'object_name': 'SubmittedImage', '_ormbases': ['submission.SubmittedComponent']},
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.ImageComponent']"}),
            'image': ('django.db.models.fields.files.FileField', [], {'max_length': '500'}),
            u'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submittedoffice': {
            'Meta': {'ordering': "['submit_time']", 'object_name': 'SubmittedOffice', '_ormbases': ['submission.SubmittedComponent']},
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.OfficeComponent']"}),
            'office': ('django.db.models.fields.files.FileField', [], {'max_length': '500'}),
            u'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submittedpdf': {
            'Meta': {'ordering': "['submit_time']", 'object_name': 'SubmittedPDF', '_ormbases': ['submission.SubmittedComponent']},
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.PDFComponent']"}),
            'pdf': ('django.db.models.fields.files.FileField', [], {'max_length': '500'}),
            u'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.submittedurl': {
            'Meta': {'ordering': "['submit_time']", 'object_name': 'SubmittedURL', '_ormbases': ['submission.SubmittedComponent']},
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.URLComponent']"}),
            u'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'submission.submittedword': {
            'Meta': {'ordering': "['submit_time']", 'object_name': 'SubmittedWord', '_ormbases': ['submission.SubmittedComponent']},
            'component': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['submission.WordComponent']"}),
            u'submittedcomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmittedComponent']", 'unique': 'True', 'primary_key': 'True'}),
            'word': ('django.db.models.fields.files.FileField', [], {'max_length': '500'})
        },
        'submission.urlcomponent': {
            'Meta': {'ordering': "['position']", 'object_name': 'URLComponent', '_ormbases': ['submission.SubmissionComponent']},
            'check': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'prefix': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        },
        'submission.wordcomponent': {
            'Meta': {'ordering': "['position']", 'object_name': 'WordComponent', '_ormbases': ['submission.SubmissionComponent']},
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '10000'}),
            u'submissioncomponent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['submission.SubmissionComponent']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['submission']