# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'EventConfig', fields ['unit', 'event_type']
        db.create_unique(u'faculty_eventconfig', ['unit_id', 'event_type'])


        # Changing field 'FacultyMemberInfo.phone_number'
        db.alter_column(u'faculty_facultymemberinfo', 'phone_number', self.gf('django.db.models.fields.CharField')(max_length=20, null=True))

        # Changing field 'FacultyMemberInfo.birthday'
        db.alter_column(u'faculty_facultymemberinfo', 'birthday', self.gf('django.db.models.fields.DateField')(null=True))

        # Changing field 'FacultyMemberInfo.office_number'
        db.alter_column(u'faculty_facultymemberinfo', 'office_number', self.gf('django.db.models.fields.CharField')(max_length=20, null=True))

    def backwards(self, orm):
        # Removing unique constraint on 'EventConfig', fields ['unit', 'event_type']
        db.delete_unique(u'faculty_eventconfig', ['unit_id', 'event_type'])


        # User chose to not deal with backwards NULL issues for 'FacultyMemberInfo.phone_number'
        raise RuntimeError("Cannot reverse this migration. 'FacultyMemberInfo.phone_number' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'FacultyMemberInfo.phone_number'
        db.alter_column(u'faculty_facultymemberinfo', 'phone_number', self.gf('django.db.models.fields.CharField')(max_length=20))

        # User chose to not deal with backwards NULL issues for 'FacultyMemberInfo.birthday'
        raise RuntimeError("Cannot reverse this migration. 'FacultyMemberInfo.birthday' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'FacultyMemberInfo.birthday'
        db.alter_column(u'faculty_facultymemberinfo', 'birthday', self.gf('django.db.models.fields.DateField')())

        # User chose to not deal with backwards NULL issues for 'FacultyMemberInfo.office_number'
        raise RuntimeError("Cannot reverse this migration. 'FacultyMemberInfo.office_number' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'FacultyMemberInfo.office_number'
        db.alter_column(u'faculty_facultymemberinfo', 'office_number', self.gf('django.db.models.fields.CharField')(max_length=20))

    models = {
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
            'userid': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '8', 'unique': 'True', 'null': 'True', 'blank': 'True'})
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
        u'faculty.careerevent': {
            'Meta': {'ordering': "('-start_date', '-end_date', 'event_type')", 'object_name': 'CareerEvent'},
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'flags': ('django.db.models.fields.BigIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'career_events'", 'to': u"orm['coredata.Person']"}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': "('person', 'unit')", 'max_length': '50', 'populate_from': "'slug_string'"}),
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
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': "'title'"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        },
        u'faculty.eventconfig': {
            'Meta': {'unique_together': "(('unit', 'event_type'),)", 'object_name': 'EventConfig'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.facultymemberinfo': {
            'Meta': {'object_name': 'FacultyMemberInfo'},
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'emergency_contact': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'office_number': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'unique': 'True', 'to': u"orm['coredata.Person']"}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'faculty.grant': {
            'Meta': {'object_name': 'Grant'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'expiry_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
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
            'Meta': {'object_name': 'GrantBalance'},
            'actual': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'balance': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'grant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.Grant']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'month': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'})
        },
        u'faculty.grantowner': {
            'Meta': {'object_name': 'GrantOwner'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}', 'null': 'True', 'blank': 'True'}),
            'grant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.Grant']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']"})
        },
        u'faculty.memo': {
            'Meta': {'object_name': 'Memo'},
            'career_event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.CareerEvent']"}),
            'cc_lines': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['coredata.Person']"}),
            'from_lines': ('django.db.models.fields.TextField', [], {}),
            'from_person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'null': 'True', 'to': u"orm['coredata.Person']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memo_text': ('django.db.models.fields.TextField', [], {}),
            'sent_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': 'None', 'unique_with': '()'}),
            'subject': ('django.db.models.fields.TextField', [], {}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['faculty.MemoTemplate']", 'null': 'True'}),
            'to_lines': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.memotemplate': {
            'Meta': {'unique_together': "(('unit', 'label'),)", 'object_name': 'MemoTemplate'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['coredata.Person']"}),
            'event_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'populate_from': 'None'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_text': ('django.db.models.fields.TextField', [], {}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Unit']"})
        },
        u'faculty.tempgrant': {
            'Meta': {'object_name': 'TempGrant'},
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['coredata.Person']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'initial': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'project_code': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        }
    }

    complete_apps = ['faculty']