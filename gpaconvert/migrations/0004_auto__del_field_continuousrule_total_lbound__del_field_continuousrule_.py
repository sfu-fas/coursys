# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'ContinuousRule.total_lbound'
        db.delete_column(u'gpaconvert_continuousrule', 'total_lbound')

        # Deleting field 'ContinuousRule.total_ubound'
        db.delete_column(u'gpaconvert_continuousrule', 'total_ubound')

        # Adding field 'GradeSource.lower_bound'
        db.add_column(u'gpaconvert_gradesource', 'lower_bound',
                      self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=8, decimal_places=2),
                      keep_default=False)

        # Adding field 'GradeSource.upper_bound'
        db.add_column(u'gpaconvert_gradesource', 'upper_bound',
                      self.gf('django.db.models.fields.DecimalField')(default='100.00', max_digits=8, decimal_places=2),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'ContinuousRule.total_lbound'
        db.add_column(u'gpaconvert_continuousrule', 'total_lbound',
                      self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=8, decimal_places=2),
                      keep_default=False)

        # Adding field 'ContinuousRule.total_ubound'
        db.add_column(u'gpaconvert_continuousrule', 'total_ubound',
                      self.gf('django.db.models.fields.DecimalField')(default='100.00', max_digits=8, decimal_places=2),
                      keep_default=False)

        # Deleting field 'GradeSource.lower_bound'
        db.delete_column(u'gpaconvert_gradesource', 'lower_bound')

        # Deleting field 'GradeSource.upper_bound'
        db.delete_column(u'gpaconvert_gradesource', 'upper_bound')


    models = {
        u'gpaconvert.continuousrule': {
            'Meta': {'unique_together': "(('grade_source', 'lookup_lbound'),)", 'object_name': 'ContinuousRule'},
            'grade_source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'continuous_rules'", 'to': u"orm['gpaconvert.GradeSource']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lookup_lbound': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
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
            'lower_bound': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '8', 'decimal_places': '2'}),
            'scale': ('django.db.models.fields.CharField', [], {'default': "'DISC'", 'max_length': '4'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'ACTI'", 'max_length': '4'}),
            'upper_bound': ('django.db.models.fields.DecimalField', [], {'default': "'100.00'", 'max_digits': '8', 'decimal_places': '2'})
        },
        u'gpaconvert.userarchive': {
            'Meta': {'object_name': 'UserArchive'},
            'data': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '64'})
        }
    }

    complete_apps = ['gpaconvert']