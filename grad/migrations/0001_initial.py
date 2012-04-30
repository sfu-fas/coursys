# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'GradProgram'
        db.create_table('grad_gradprogram', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('modified_by', self.gf('django.db.models.fields.CharField')(max_length=32, null=True)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=(), max_length=50, populate_from=None, db_index=True)),
        ))
        db.send_create_signal('grad', ['GradProgram'])

        # Adding unique constraint on 'GradProgram', fields ['unit', 'label']
        db.create_unique('grad_gradprogram', ['unit_id', 'label'])

        # Adding model 'GradStudent'
        db.create_table('grad_gradstudent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'])),
            ('program', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradProgram'])),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=(), db_index=True)),
            ('research_area', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('campus', self.gf('django.db.models.fields.CharField')(max_length=5, blank=True)),
            ('english_fluency', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('mother_tongue', self.gf('django.db.models.fields.CharField')(max_length=25, blank=True)),
            ('is_canadian', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('passport_issued_by', self.gf('django.db.models.fields.CharField')(max_length=25, blank=True)),
            ('special_arrangements', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('comments', self.gf('django.db.models.fields.TextField')(max_length=250, blank=True)),
            ('application_status', self.gf('django.db.models.fields.CharField')(default='UNKN', max_length=4)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('modified_by', self.gf('django.db.models.fields.CharField')(max_length=32, null=True)),
            ('config', self.gf('jsonfield.JSONField')(default={})),
        ))
        db.send_create_signal('grad', ['GradStudent'])

        # Adding model 'Supervisor'
        db.create_table('grad_supervisor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradStudent'])),
            ('supervisor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'], null=True, blank=True)),
            ('external', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('position', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('supervisor_type', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('removed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('modified_by', self.gf('django.db.models.fields.CharField')(max_length=32, null=True)),
            ('config', self.gf('jsonfield.JSONField')(default={})),
        ))
        db.send_create_signal('grad', ['Supervisor'])

        # Adding model 'GradRequirement'
        db.create_table('grad_gradrequirement', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('program', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradProgram'])),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('grad', ['GradRequirement'])

        # Adding model 'CompletedRequirement'
        db.create_table('grad_completedrequirement', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('requirement', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradRequirement'])),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradStudent'])),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Semester'])),
            ('date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('grad', ['CompletedRequirement'])

        # Adding model 'GradStatus'
        db.create_table('grad_gradstatus', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradStudent'])),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('start', self.gf('django.db.models.fields.related.ForeignKey')(related_name='start_semester', to=orm['coredata.Semester'])),
            ('start_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('end', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='end_semester', null=True, to=orm['coredata.Semester'])),
            ('notes', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
        ))
        db.send_create_signal('grad', ['GradStatus'])

        # Adding model 'LetterTemplate'
        db.create_table('grad_lettertemplate', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=(), max_length=50, populate_from=None, db_index=True)),
        ))
        db.send_create_signal('grad', ['LetterTemplate'])

        # Adding unique constraint on 'LetterTemplate', fields ['unit', 'label']
        db.create_unique('grad_lettertemplate', ['unit_id', 'label'])

        # Adding model 'Letter'
        db.create_table('grad_letter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradStudent'])),
            ('date', self.gf('django.db.models.fields.DateField')()),
            ('to_lines', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('template', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.LetterTemplate'])),
            ('salutation', self.gf('django.db.models.fields.CharField')(default='To whom it may concern', max_length=100)),
            ('closing', self.gf('django.db.models.fields.CharField')(default='Yours truly', max_length=100)),
            ('from_person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'], null=True)),
            ('from_lines', self.gf('django.db.models.fields.TextField')()),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('config', self.gf('jsonfield.JSONField')(default={})),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique=True, max_length=50, populate_from=None, unique_with=(), db_index=True)),
        ))
        db.send_create_signal('grad', ['Letter'])

        # Adding model 'ScholarshipType'
        db.create_table('grad_scholarshiptype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Unit'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('eligible', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('grad', ['ScholarshipType'])

        # Adding model 'Scholarship'
        db.create_table('grad_scholarship', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('scholarship_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.ScholarshipType'])),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradStudent'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('start_semester', self.gf('django.db.models.fields.related.ForeignKey')(related_name='scholarship_start', to=orm['coredata.Semester'])),
            ('end_semester', self.gf('django.db.models.fields.related.ForeignKey')(related_name='scholarship_end', to=orm['coredata.Semester'])),
            ('comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('grad', ['Scholarship'])

        # Adding model 'OtherFunding'
        db.create_table('grad_otherfunding', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradStudent'])),
            ('semester', self.gf('django.db.models.fields.related.ForeignKey')(related_name='other_funding', to=orm['coredata.Semester'])),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('eligible', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('grad', ['OtherFunding'])

        # Adding model 'Promise'
        db.create_table('grad_promise', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grad.GradStudent'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('start_semester', self.gf('django.db.models.fields.related.ForeignKey')(related_name='promise_start', to=orm['coredata.Semester'])),
            ('end_semester', self.gf('django.db.models.fields.related.ForeignKey')(related_name='promise_end', to=orm['coredata.Semester'])),
            ('comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('grad', ['Promise'])

        # Adding model 'SavedSearch'
        db.create_table('grad_savedsearch', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Person'], null=True)),
            ('query', self.gf('django.db.models.fields.TextField')()),
            ('config', self.gf('jsonfield.JSONField')(default={})),
        ))
        db.send_create_signal('grad', ['SavedSearch'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'LetterTemplate', fields ['unit', 'label']
        db.delete_unique('grad_lettertemplate', ['unit_id', 'label'])

        # Removing unique constraint on 'GradProgram', fields ['unit', 'label']
        db.delete_unique('grad_gradprogram', ['unit_id', 'label'])

        # Deleting model 'GradProgram'
        db.delete_table('grad_gradprogram')

        # Deleting model 'GradStudent'
        db.delete_table('grad_gradstudent')

        # Deleting model 'Supervisor'
        db.delete_table('grad_supervisor')

        # Deleting model 'GradRequirement'
        db.delete_table('grad_gradrequirement')

        # Deleting model 'CompletedRequirement'
        db.delete_table('grad_completedrequirement')

        # Deleting model 'GradStatus'
        db.delete_table('grad_gradstatus')

        # Deleting model 'LetterTemplate'
        db.delete_table('grad_lettertemplate')

        # Deleting model 'Letter'
        db.delete_table('grad_letter')

        # Deleting model 'ScholarshipType'
        db.delete_table('grad_scholarshiptype')

        # Deleting model 'Scholarship'
        db.delete_table('grad_scholarship')

        # Deleting model 'OtherFunding'
        db.delete_table('grad_otherfunding')

        # Deleting model 'Promise'
        db.delete_table('grad_promise')

        # Deleting model 'SavedSearch'
        db.delete_table('grad_savedsearch')


    models = {
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
        'grad.completedrequirement': {
            'Meta': {'object_name': 'CompletedRequirement'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requirement': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradRequirement']"}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Semester']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradStudent']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'grad.gradprogram': {
            'Meta': {'unique_together': "(('unit', 'label'),)", 'object_name': 'GradProgram'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'modified_by': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None', 'db_index': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'grad.gradrequirement': {
            'Meta': {'object_name': 'GradRequirement'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradProgram']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'grad.gradstatus': {
            'Meta': {'object_name': 'GradStatus'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'end_semester'", 'null': 'True', 'to': "orm['coredata.Semester']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'start': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'start_semester'", 'to': "orm['coredata.Semester']"}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradStudent']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'grad.gradstudent': {
            'Meta': {'object_name': 'GradStudent'},
            'application_status': ('django.db.models.fields.CharField', [], {'default': "'UNKN'", 'max_length': '4'}),
            'campus': ('django.db.models.fields.CharField', [], {'max_length': '5', 'blank': 'True'}),
            'comments': ('django.db.models.fields.TextField', [], {'max_length': '250', 'blank': 'True'}),
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'english_fluency': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_canadian': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'modified_by': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'mother_tongue': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'passport_issued_by': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']"}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradProgram']"}),
            'research_area': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()', 'db_index': 'True'}),
            'special_arrangements': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'grad.letter': {
            'Meta': {'object_name': 'Letter'},
            'closing': ('django.db.models.fields.CharField', [], {'default': "'Yours truly'", 'max_length': '100'}),
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'from_lines': ('django.db.models.fields.TextField', [], {}),
            'from_person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'salutation': ('django.db.models.fields.CharField', [], {'default': "'To whom it may concern'", 'max_length': '100'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()', 'db_index': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradStudent']"}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.LetterTemplate']"}),
            'to_lines': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'grad.lettertemplate': {
            'Meta': {'unique_together': "(('unit', 'label'),)", 'object_name': 'LetterTemplate'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None', 'db_index': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'grad.otherfunding': {
            'Meta': {'object_name': 'OtherFunding'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'eligible': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'other_funding'", 'to': "orm['coredata.Semester']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradStudent']"})
        },
        'grad.promise': {
            'Meta': {'object_name': 'Promise'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'promise_end'", 'to': "orm['coredata.Semester']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'promise_start'", 'to': "orm['coredata.Semester']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradStudent']"})
        },
        'grad.savedsearch': {
            'Meta': {'object_name': 'SavedSearch'},
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']", 'null': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {})
        },
        'grad.scholarship': {
            'Meta': {'object_name': 'Scholarship'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'scholarship_end'", 'to': "orm['coredata.Semester']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'scholarship_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.ScholarshipType']"}),
            'start_semester': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'scholarship_start'", 'to': "orm['coredata.Semester']"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradStudent']"})
        },
        'grad.scholarshiptype': {
            'Meta': {'object_name': 'ScholarshipType'},
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'eligible': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Unit']"})
        },
        'grad.supervisor': {
            'Meta': {'object_name': 'Supervisor'},
            'config': ('jsonfield.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'external': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_by': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'position': ('django.db.models.fields.SmallIntegerField', [], {}),
            'removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grad.GradStudent']"}),
            'supervisor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Person']", 'null': 'True', 'blank': 'True'}),
            'supervisor_type': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['grad']
