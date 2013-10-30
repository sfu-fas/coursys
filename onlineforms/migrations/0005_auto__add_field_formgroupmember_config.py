# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'FormGroupMember.config'
        db.add_column('onlineforms_formgroup_members', 'config',
                      self.gf('jsonfield.fields.JSONField')(default={}),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'FormGroupMember.config'
        db.delete_column('onlineforms_formgroup_members', 'config')


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
        'onlineforms.field': {
            'Meta': {'unique_together': "(('sheet', 'slug'),)", 'object_name': 'Field'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fieldtype': ('django.db.models.fields.CharField', [], {'default': "'SMTX'", 'max_length': '4'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'original': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.Field']", 'null': 'True', 'blank': 'True'}),
            'sheet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.Sheet']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'})
        },
        'onlineforms.fieldsubmission': {
            'Meta': {'object_name': 'FieldSubmission'},
            'data': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'field': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.Field']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sheet_submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.SheetSubmission']"})
        },
        'onlineforms.fieldsubmissionfile': {
            'Meta': {'object_name': 'FieldSubmissionFile'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'field_submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.FieldSubmission']", 'unique': 'True'}),
            'file_attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'file_mediatype': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'onlineforms.form': {
            'Meta': {'object_name': 'Form'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'advisor_visible': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiators': ('django.db.models.fields.CharField', [], {'default': "'NON'", 'max_length': '3'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'original': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.Form']", 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.FormGroup']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'onlineforms.formfiller': {
            'Meta': {'object_name': 'FormFiller'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nonSFUFormFiller': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.NonSFUFormFiller']", 'null': 'True'}),
            'sfuFormFiller': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']", 'null': 'True'})
        },
        'onlineforms.formgroup': {
            'Meta': {'unique_together': "(('unit', 'name'),)", 'object_name': 'FormGroup'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['coredata.Person']", 'through': "orm['onlineforms.FormGroupMember']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'onlineforms.formgroupmember': {
            'Meta': {'unique_together': "(('person', 'formgroup'),)", 'object_name': 'FormGroupMember', 'db_table': "'onlineforms_formgroup_members'"},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'formgroup': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.FormGroup']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"})
        },
        'onlineforms.formsubmission': {
            'Meta': {'object_name': 'FormSubmission'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.Form']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.FormFiller']"}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.FormGroup']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'PEND'", 'max_length': '4'})
        },
        'onlineforms.nonsfuformfiller': {
            'Meta': {'object_name': 'NonSFUFormFiller'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'email_address': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'onlineforms.sheet': {
            'Meta': {'ordering': "('order',)", 'unique_together': "(('form', 'slug'),)", 'object_name': 'Sheet'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_view': ('django.db.models.fields.CharField', [], {'default': "'NON'", 'max_length': '4'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.Form']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_initial': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'original': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.Sheet']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '60'})
        },
        'onlineforms.sheetsubmission': {
            'Meta': {'object_name': 'SheetSubmission'},
            'completed_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'filler': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.FormFiller']"}),
            'form_submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.FormSubmission']"}),
            'given_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sheet': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.Sheet']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'WAIT'", 'max_length': '4'})
        },
        'onlineforms.sheetsubmissionsecreturl': {
            'Meta': {'object_name': 'SheetSubmissionSecretUrl'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'sheet_submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.SheetSubmission']"})
        }
    }

    complete_apps = ['onlineforms']