# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'GradeSource'
        db.create_table(u'gpaconvert_gradesource', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('country', self.gf('django_countries.fields.CountryField')(max_length=2)),
            ('institution', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
            ('status', self.gf('django.db.models.fields.CharField')(default='ACTI', max_length=4)),
            ('scale', self.gf('django.db.models.fields.CharField')(default='DISC', max_length=4)),
            ('slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=(), max_length=50, populate_from=None)),
        ))
        db.send_create_signal(u'gpaconvert', ['GradeSource'])

        # Adding unique constraint on 'GradeSource', fields ['country', 'institution']
        db.create_unique(u'gpaconvert_gradesource', ['country', 'institution'])

        # Adding model 'DiscreteRule'
        db.create_table(u'gpaconvert_discreterule', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('grade_source', self.gf('django.db.models.fields.related.ForeignKey')(related_name='discrete_rules', to=orm['gpaconvert.GradeSource'])),
            ('lookup_value', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('transfer_value', self.gf('django.db.models.fields.CharField')(max_length=2)),
        ))
        db.send_create_signal(u'gpaconvert', ['DiscreteRule'])

        # Adding unique constraint on 'DiscreteRule', fields ['grade_source', 'lookup_value']
        db.create_unique(u'gpaconvert_discreterule', ['grade_source_id', 'lookup_value'])

        # Adding model 'ContinuousRule'
        db.create_table(u'gpaconvert_continuousrule', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('grade_source', self.gf('django.db.models.fields.related.ForeignKey')(related_name='continuous_rules', to=orm['gpaconvert.GradeSource'])),
            ('total_lbound', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=8, decimal_places=2)),
            ('total_ubound', self.gf('django.db.models.fields.DecimalField')(default='100.00', max_digits=8, decimal_places=2)),
            ('lookup_lbound', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('transfer_value', self.gf('django.db.models.fields.CharField')(max_length=2)),
        ))
        db.send_create_signal(u'gpaconvert', ['ContinuousRule'])

        # Adding unique constraint on 'ContinuousRule', fields ['grade_source', 'lookup_lbound']
        db.create_unique(u'gpaconvert_continuousrule', ['grade_source_id', 'lookup_lbound'])

        # Adding model 'UserArchive'
        db.create_table(u'gpaconvert_userarchive', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=64)),
            ('data', self.gf('jsonfield.fields.JSONField')(default={})),
        ))
        db.send_create_signal(u'gpaconvert', ['UserArchive'])


    def backwards(self, orm):
        # Removing unique constraint on 'ContinuousRule', fields ['grade_source', 'lookup_lbound']
        db.delete_unique(u'gpaconvert_continuousrule', ['grade_source_id', 'lookup_lbound'])

        # Removing unique constraint on 'DiscreteRule', fields ['grade_source', 'lookup_value']
        db.delete_unique(u'gpaconvert_discreterule', ['grade_source_id', 'lookup_value'])

        # Removing unique constraint on 'GradeSource', fields ['country', 'institution']
        db.delete_unique(u'gpaconvert_gradesource', ['country', 'institution'])

        # Deleting model 'GradeSource'
        db.delete_table(u'gpaconvert_gradesource')

        # Deleting model 'DiscreteRule'
        db.delete_table(u'gpaconvert_discreterule')

        # Deleting model 'ContinuousRule'
        db.delete_table(u'gpaconvert_continuousrule')

        # Deleting model 'UserArchive'
        db.delete_table(u'gpaconvert_userarchive')


    models = {
        u'gpaconvert.continuousrule': {
            'Meta': {'unique_together': "(('grade_source', 'lookup_lbound'),)", 'object_name': 'ContinuousRule'},
            'grade_source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'continuous_rules'", 'to': u"orm['gpaconvert.GradeSource']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lookup_lbound': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'total_lbound': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '8', 'decimal_places': '2'}),
            'total_ubound': ('django.db.models.fields.DecimalField', [], {'default': "'100.00'", 'max_digits': '8', 'decimal_places': '2'}),
            'transfer_value': ('django.db.models.fields.CharField', [], {'max_length': '2'})
        },
        u'gpaconvert.discreterule': {
            'Meta': {'unique_together': "(('grade_source', 'lookup_value'),)", 'object_name': 'DiscreteRule'},
            'grade_source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'discrete_rules'", 'to': u"orm['gpaconvert.GradeSource']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lookup_value': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'transfer_value': ('django.db.models.fields.CharField', [], {'max_length': '2'})
        },
        u'gpaconvert.gradesource': {
            'Meta': {'unique_together': "(('country', 'institution'),)", 'object_name': 'GradeSource'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'country': ('django_countries.fields.CountryField', [], {'max_length': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'scale': ('django.db.models.fields.CharField', [], {'default': "'DISC'", 'max_length': '4'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'ACTI'", 'max_length': '4'})
        },
        u'gpaconvert.userarchive': {
            'Meta': {'object_name': 'UserArchive'},
            'data': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'})
        }
    }

    complete_apps = ['gpaconvert']