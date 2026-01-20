from django.db import models

# Migrating to Django 4 to 5 on MariaDB needs a hack to make legacy database schema transition smoothly.
# https://www.albertyw.com/note/django-5-mariadb-uuidfield

# Django 4 on mariadb: djamgo.db.models.UUIDFields were represented as CHAR(32).
# Django 4 + this UUIDField: migrations change the mariadb field type to UUID (preserving/converting the values).
# Django 5 on mariadb: field type is UUID, matching this, for seamless transition.
# Once cleanly on Django 5, fields may be reverted to models.UUIDField and this file can be discarded.

class UUIDField(models.UUIDField):
    def db_type(self, connection):
       return "uuid"
