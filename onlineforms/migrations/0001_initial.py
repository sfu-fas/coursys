# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'NonSFUFormFiller'
        db.create_table('onlineforms_nonsfuformfiller', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('email_address', self.gf('django.db.models.fields.EmailField')(max_length=254)),
        ))
        db.send_create_signal('onlineforms', ['NonSFUFormFiller'])

        # Adding model 'FormFiller'
        db.create_table('onlineforms_formfiller', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sfuFormFiller', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'], null=True)),
            ('nonSFUFormFiller', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.NonSFUFormFiller'], null=True)),
        ))
        db.send_create_signal('onlineforms', ['FormFiller'])

        # Adding model 'FormGroup'
        db.create_table('onlineforms_formgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=60)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
        ))
        db.send_create_signal('onlineforms', ['FormGroup'])

        # Adding unique constraint on 'FormGroup', fields ['unit', 'name']
        db.create_unique('onlineforms_formgroup', ['unit_id', 'name'])

        # Adding M2M table for field members on 'FormGroup'
        db.create_table('onlineforms_formgroup_members', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('formgroup', models.ForeignKey(orm['onlineforms.formgroup'], null=False)),
            ('person', models.ForeignKey(orm['coredata.person'], null=False))
        ))
        db.create_unique('onlineforms_formgroup_members', ['formgroup_id', 'person_id'])

        # Adding model 'Form'
        db.create_table('onlineforms_form', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=60)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.FormGroup'])),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('initiators', self.gf('django.db.models.fields.CharField')(default='NON', max_length=3)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('original', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.Form'], null=True, blank=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=())),
        ))
        db.send_create_signal('onlineforms', ['Form'])

        # Adding model 'Sheet'
        db.create_table('onlineforms_sheet', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=60)),
            ('form', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.Form'])),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('is_initial', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('can_view', self.gf('django.db.models.fields.CharField')(default='NON', max_length=4)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('original', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.Sheet'], null=True, blank=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=(), max_length=50, populate_from=None)),
        ))
        db.send_create_signal('onlineforms', ['Sheet'])

        # Adding model 'Field'
        db.create_table('onlineforms_field', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=60)),
            ('sheet', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.Sheet'])),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('fieldtype', self.gf('django.db.models.fields.CharField')(default='SMTX', max_length=4)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('original', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.Field'], null=True, blank=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=(), max_length=50, populate_from=None)),
        ))
        db.send_create_signal('onlineforms', ['Field'])

        # Adding model 'FormSubmission'
        db.create_table('onlineforms_formsubmission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('form', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.Form'])),
            ('initiator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.FormFiller'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.FormGroup'])),
            ('status', self.gf('django.db.models.fields.CharField')(default='PEND', max_length=4)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=(), max_length=50, populate_from=None)),
        ))
        db.send_create_signal('onlineforms', ['FormSubmission'])

        # Adding model 'SheetSubmission'
        db.create_table('onlineforms_sheetsubmission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('form_submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.FormSubmission'])),
            ('sheet', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.Sheet'])),
            ('filler', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.FormFiller'])),
            ('status', self.gf('django.db.models.fields.CharField')(default='WAIT', max_length=4)),
            ('given_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('completed_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=(), max_length=50, populate_from=None)),
        ))
        db.send_create_signal('onlineforms', ['SheetSubmission'])

        # Adding model 'FieldSubmission'
        db.create_table('onlineforms_fieldsubmission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sheet_submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.SheetSubmission'])),
            ('field', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.Field'])),
            ('data', self.gf('jsonfield.fields.JSONField')(default={})),
        ))
        db.send_create_signal('onlineforms', ['FieldSubmission'])

        # Adding model 'FieldSubmissionFile'
        db.create_table('onlineforms_fieldsubmissionfile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('field_submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.FieldSubmission'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('file_attachment', self.gf('django.db.models.fields.files.FileField')(max_length=500, null=True, blank=True)),
            ('file_mediatype', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
        ))
        db.send_create_signal('onlineforms', ['FieldSubmissionFile'])

        # Adding model 'SheetSubmissionSecretUrl'
        db.create_table('onlineforms_sheetsubmissionsecreturl', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sheet_submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['onlineforms.SheetSubmission'])),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
        ))
        db.send_create_signal('onlineforms', ['SheetSubmissionSecretUrl'])


    def backwards(self, orm):
        # Removing unique constraint on 'FormGroup', fields ['unit', 'name']
        db.delete_unique('onlineforms_formgroup', ['unit_id', 'name'])

        # Deleting model 'NonSFUFormFiller'
        db.delete_table('onlineforms_nonsfuformfiller')

        # Deleting model 'FormFiller'
        db.delete_table('onlineforms_formfiller')

        # Deleting model 'FormGroup'
        db.delete_table('onlineforms_formgroup')

        # Removing M2M table for field members on 'FormGroup'
        db.delete_table('onlineforms_formgroup_members')

        # Deleting model 'Form'
        db.delete_table('onlineforms_form')

        # Deleting model 'Sheet'
        db.delete_table('onlineforms_sheet')

        # Deleting model 'Field'
        db.delete_table('onlineforms_field')

        # Deleting model 'FormSubmission'
        db.delete_table('onlineforms_formsubmission')

        # Deleting model 'SheetSubmission'
        db.delete_table('onlineforms_sheetsubmission')

        # Deleting model 'FieldSubmission'
        db.delete_table('onlineforms_fieldsubmission')

        # Deleting model 'FieldSubmissionFile'
        db.delete_table('onlineforms_fieldsubmissionfile')

        # Deleting model 'SheetSubmissionSecretUrl'
        db.delete_table('onlineforms_sheetsubmissionsecreturl')


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
            'Meta': {'object_name': 'Field'},
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
            'field_submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.FieldSubmission']"}),
            'file_attachment': ('django.db.models.fields.files.FileField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'file_mediatype': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'onlineforms.form': {
            'Meta': {'object_name': 'Form'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
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
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'nonSFUFormFiller': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.NonSFUFormFiller']", 'null': 'True'}),
            'sfuFormFiller': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']", 'null': 'True'})
        },
        'onlineforms.formgroup': {
            'Meta': {'unique_together': "(('unit', 'name'),)", 'object_name': 'FormGroup'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['coredata.Person']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'onlineforms.formsubmission': {
            'Meta': {'object_name': 'FormSubmission'},
            'form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.Form']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.FormFiller']"}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['onlineforms.FormGroup']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'PEND'", 'max_length': '4'})
        },
        'onlineforms.nonsfuformfiller': {
            'Meta': {'object_name': 'NonSFUFormFiller'},
            'email_address': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'onlineforms.sheet': {
            'Meta': {'object_name': 'Sheet'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_view': ('django.db.models.fields.CharField', [], {'default': "'NON'", 'max_length': '4'}),
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