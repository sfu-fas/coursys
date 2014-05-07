# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'EventConfig.config'
        db.alter_column(u'faculty_eventconfig', 'config', self.gf('courselib.json_fields.JSONField')())

        # Changing field 'Memo.config'
        db.alter_column(u'faculty_memo', 'config', self.gf('courselib.json_fields.JSONField')())

        # Changing field 'CareerEvent.config'
        db.alter_column(u'faculty_careerevent', 'config', self.gf('courselib.json_fields.JSONField')())

        # Changing field 'CareerEvent.slug'
        db.alter_column(u'faculty_careerevent', 'slug', self.gf('autoslug.fields.AutoSlugField')(unique_with=('person',), max_length=50, populate_from='slug_string'))
        # Adding unique constraint on 'CareerEvent', fields ['person', 'slug']
        db.create_unique(u'faculty_careerevent', ['person_id', 'slug'])


        # Changing field 'FacultyMemberInfo.config'
        db.alter_column(u'faculty_facultymemberinfo', 'config', self.gf('courselib.json_fields.JSONField')(null=True))

        # Changing field 'GrantBalance.config'
        db.alter_column(u'faculty_grantbalance', 'config', self.gf('courselib.json_fields.JSONField')(null=True))

        # Changing field 'TempGrant.config'
        db.alter_column(u'faculty_tempgrant', 'config', self.gf('courselib.json_fields.JSONField')())

        # Changing field 'Grant.config'
        db.alter_column(u'faculty_grant', 'config', self.gf('courselib.json_fields.JSONField')(null=True))

        # Changing field 'GrantOwner.config'
        db.alter_column(u'faculty_grantowner', 'config', self.gf('courselib.json_fields.JSONField')(null=True))

    def backwards(self, orm):
        # Removing unique constraint on 'CareerEvent', fields ['person', 'slug']
        db.delete_unique(u'faculty_careerevent', ['person_id', 'slug'])


        # Changing field 'EventConfig.config'
        db.alter_column(u'faculty_eventconfig', 'config', self.gf('jsonfield.fields.JSONField')())

        # Changing field 'Memo.config'
        db.alter_column(u'faculty_memo', 'config', self.gf('jsonfield.fields.JSONField')())

        # Changing field 'CareerEvent.config'
        db.alter_column(u'faculty_careerevent', 'config', self.gf('jsonfield.fields.JSONField')())

        # Changing field 'CareerEvent.slug'
        db.alter_column(u'faculty_careerevent', 'slug', self.gf('autoslug.fields.AutoSlugField')(max_length=50, unique_with=('person', 'unit'), populate_from='slug_string'))

        # Changing field 'FacultyMemberInfo.config'
        db.alter_column(u'faculty_facultymemberinfo', 'config', self.gf('jsonfield.fields.JSONField')(null=True))

        # Changing field 'GrantBalance.config'
        db.alter_column(u'faculty_grantbalance', 'config', self.gf('jsonfield.fields.JSONField')(null=True))

        # Changing field 'TempGrant.config'
        db.alter_column(u'faculty_tempgrant', 'config', self.gf('jsonfield.fields.JSONField')())

        # Changing field 'Grant.config'
        db.alter_column(u'faculty_grant', 'config', self.gf('jsonfield.fields.JSONField')(null=True))

        # Changing field 'GrantOwner.config'
        db.alter_column(u'faculty_grantowner', 'config', self.gf('jsonfield.fields.JSONField')(null=True))

    models = {
        u'coredata.person': {
            'Meta': {'ordering': "['last_name', 'first_name', 'userid']", 'object_name': 'Person'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'emplid': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'db_index': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'pref_first_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '8', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'coredata.unit': {
            'Meta': {'ordering': "['label']", 'object_name': 'Unit'},
            'acad_org': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '4', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']", 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'})
        },
        u'faculty.careerevent': {
            'Meta': {'ordering': "('-start_date', '-end_date', 'event_type')", 'unique_together': "(('person', 'slug'),)", 'object_name': 'CareerEvent'},
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'flags': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'career_events'", 'to': u"orm['coredata.Person']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('person',)", 'max_length': '50', 'populate_from': "'slug_string'"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '2'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.documentattachment': {
            'Meta': {'ordering': "('created_at',)", 'unique_together': "(('career_event', 'slug'),)", 'object_name': 'DocumentAttachment'},
            'career_event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attachments'", 'to': u"orm['faculty.CareerEvent']"}),
            'contents': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mediatype': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('career_event',)", 'max_length': '50', 'populate_from': "'title'"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        },
        u'faculty.eventconfig': {
            'Meta': {'unique_together': "(('unit', 'event_type'),)", 'object_name': 'EventConfig'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.facultymemberinfo': {
            'Meta': {'object_name': 'FacultyMemberInfo'},
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'emergency_contact': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'office_number': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'unique': 'True', 'to': u"orm['coredata.Person']"}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'faculty.grant': {
            'Meta': {'ordering': "['title']", 'unique_together': "(('label', 'unit'),)", 'object_name': 'Grant'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'expiry_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'overhead': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'owners': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['coredata.Person']", 'null': 'True', 'through': u"orm['faculty.GrantOwner']", 'symmetrical': 'False'}),
            'project_code': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('unit',)", 'max_length': '50', 'populate_from': "'title'"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'A'", 'max_length': '2'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.grantbalance': {
            'Meta': {'ordering': "['date']", 'object_name': 'GrantBalance'},
            'actual': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'balance': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'grant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.Grant']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'month': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'})
        },
        u'faculty.grantowner': {
            'Meta': {'object_name': 'GrantOwner'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'grant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.Grant']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']"})
        },
        u'faculty.memo': {
            'Meta': {'object_name': 'Memo'},
            'career_event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.CareerEvent']"}),
            'cc_lines': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['coredata.Person']"}),
            'from_lines': ('django.db.models.fields.TextField', [], {}),
            'from_person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['coredata.Person']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memo_text': ('django.db.models.fields.TextField', [], {}),
            'sent_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('career_event',)", 'max_length': '50', 'populate_from': 'None'}),
            'subject': ('django.db.models.fields.TextField', [], {}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.MemoTemplate']", 'null': 'True'}),
            'to_lines': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.memotemplate': {
            'Meta': {'unique_together': "(('unit', 'label'),)", 'object_name': 'MemoTemplate'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['coredata.Person']"}),
            'default_from': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_text': ('django.db.models.fields.TextField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.tempgrant': {
            'Meta': {'unique_together': "(('label', 'creator'),)", 'object_name': 'TempGrant'},
            'config': ('courselib.json_fields.JSONField', [], {'default': '{}'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'project_code': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        }
    }

    complete_apps = ['faculty']