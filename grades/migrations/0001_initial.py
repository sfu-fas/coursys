# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Activity'
        db.create_table('grades_activity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30, db_index=True)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=15, db_index=True)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(max_length=50, unique=False, unique_with=('offering',), db_index=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('due_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('percent', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('position', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('group', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('deleted', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True, blank=True)),
            ('offering', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.CourseOffering'])),
        ))
        db.send_create_signal('grades', ['Activity'])

        # Adding model 'NumericActivity'
        db.create_table('grades_numericactivity', (
            ('activity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['grades.Activity'], unique=True, primary_key=True)),
            ('max_grade', self.gf('django.db.models.fields.DecimalField')(max_digits=5, decimal_places=2)),
        ))
        db.send_create_signal('grades', ['NumericActivity'])

        # Adding model 'LetterActivity'
        db.create_table('grades_letteractivity', (
            ('activity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['grades.Activity'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('grades', ['LetterActivity'])

        # Adding model 'CalNumericActivity'
        db.create_table('grades_calnumericactivity', (
            ('numericactivity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['grades.NumericActivity'], unique=True, primary_key=True)),
            ('formula', self.gf('django.db.models.fields.CharField')(max_length=250)),
        ))
        db.send_create_signal('grades', ['CalNumericActivity'])

        # Adding model 'CalLetterActivity'
        db.create_table('grades_calletteractivity', (
            ('letteractivity_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['grades.LetterActivity'], unique=True, primary_key=True)),
            ('numeric_activity', self.gf('django.db.models.fields.related.ForeignKey')(related_name='numeric_source_set', to=orm['grades.NumericActivity'])),
            ('exam_activity', self.gf('django.db.models.fields.related.ForeignKey')(related_name='exam_set', null=True, to=orm['grades.Activity'])),
            ('letter_cutoff_formula', self.gf('django.db.models.fields.CharField')(max_length=250)),
        ))
        db.send_create_signal('grades', ['CalLetterActivity'])

        # Adding model 'NumericGrade'
        db.create_table('grades_numericgrade', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grades.NumericActivity'])),
            ('member', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Member'])),
            ('value', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=5, decimal_places=2)),
            ('flag', self.gf('django.db.models.fields.CharField')(default='NOGR', max_length=4)),
        ))
        db.send_create_signal('grades', ['NumericGrade'])

        # Adding unique constraint on 'NumericGrade', fields ['activity', 'member']
        db.create_unique('grades_numericgrade', ['activity_id', 'member_id'])

        # Adding model 'LetterGrade'
        db.create_table('grades_lettergrade', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['grades.LetterActivity'])),
            ('member', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['coredata.Member'])),
            ('letter_grade', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('flag', self.gf('django.db.models.fields.CharField')(default='NOGR', max_length=4)),
        ))
        db.send_create_signal('grades', ['LetterGrade'])

        # Adding unique constraint on 'LetterGrade', fields ['activity', 'member']
        db.create_unique('grades_lettergrade', ['activity_id', 'member_id'])


    def backwards(self, orm):
        
        # Deleting model 'Activity'
        db.delete_table('grades_activity')

        # Deleting model 'NumericActivity'
        db.delete_table('grades_numericactivity')

        # Deleting model 'LetterActivity'
        db.delete_table('grades_letteractivity')

        # Deleting model 'CalNumericActivity'
        db.delete_table('grades_calnumericactivity')

        # Deleting model 'CalLetterActivity'
        db.delete_table('grades_calletteractivity')

        # Deleting model 'NumericGrade'
        db.delete_table('grades_numericgrade')

        # Removing unique constraint on 'NumericGrade', fields ['activity', 'member']
        db.delete_unique('grades_numericgrade', ['activity_id', 'member_id'])

        # Deleting model 'LetterGrade'
        db.delete_table('grades_lettergrade')

        # Removing unique constraint on 'LetterGrade', fields ['activity', 'member']
        db.delete_unique('grades_lettergrade', ['activity_id', 'member_id'])


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
        'grades.calletteractivity': {
            'Meta': {'object_name': 'CalLetterActivity', '_ormbases': ['grades.LetterActivity']},
            'exam_activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'exam_set'", 'null': 'True', 'to': "orm['grades.Activity']"}),
            'letter_cutoff_formula': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'letteractivity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['grades.LetterActivity']", 'unique': 'True', 'primary_key': 'True'}),
            'numeric_activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'numeric_source_set'", 'to': "orm['grades.NumericActivity']"})
        },
        'grades.calnumericactivity': {
            'Meta': {'object_name': 'CalNumericActivity', '_ormbases': ['grades.NumericActivity']},
            'formula': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'numericactivity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['grades.NumericActivity']", 'unique': 'True', 'primary_key': 'True'})
        },
        'grades.letteractivity': {
            'Meta': {'object_name': 'LetterActivity', '_ormbases': ['grades.Activity']},
            'activity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['grades.Activity']", 'unique': 'True', 'primary_key': 'True'})
        },
        'grades.lettergrade': {
            'Meta': {'unique_together': "(('activity', 'member'),)", 'object_name': 'LetterGrade'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.LetterActivity']"}),
            'flag': ('django.db.models.fields.CharField', [], {'default': "'NOGR'", 'max_length': '4'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'letter_grade': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"})
        },
        'grades.numericactivity': {
            'Meta': {'object_name': 'NumericActivity', '_ormbases': ['grades.Activity']},
            'activity_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['grades.Activity']", 'unique': 'True', 'primary_key': 'True'}),
            'max_grade': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'})
        },
        'grades.numericgrade': {
            'Meta': {'unique_together': "(('activity', 'member'),)", 'object_name': 'NumericGrade'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['grades.NumericActivity']"}),
            'flag': ('django.db.models.fields.CharField', [], {'default': "'NOGR'", 'max_length': '4'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['coredata.Member']"}),
            'value': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '5', 'decimal_places': '2'})
        }
    }

    complete_apps = ['grades']
