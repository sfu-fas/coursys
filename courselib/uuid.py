from django.db import models

# Migrating to Django 4 to 5 on MariaDB needs a hack to make legacy database schema transition smoothly.
# https://www.albertyw.com/note/django-5-mariadb-uuidfield

# Django 4 on mariadb: django.db.models.UUIDFields were represented as CHAR(32).
# Django 4 + this UUIDField: migrations change the mariadb field type to UUID (preserving/converting the values).
# Django 5 on mariadb: field type is UUID, matching this, for seamless transition.
# Once cleanly on Django 5, fields may be reverted to models.UUIDField and this file can be discarded.

# Experimentally, a test system worked throughout both of these:
# (0) have existing data (1) merge this in with its migrations (2) dc build (3) dc up -d (4) make migrate-safe 
# (0) have existing data (1) merge this in with its migrations (2) dc build (3) make migrate-safe (4) dc up -d
# ... so the mariadb treatment of CHAR(32) and UUID must be close enough either way for django 4.

class UUIDField(models.UUIDField):
    def db_type(self, connection):
       return "uuid"
