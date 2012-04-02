# based on http://djangosnippets.org/snippets/1478/

from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
#from django.utils import simplejson as json
import json
from django.http import QueryDict

class QueryDictField(models.TextField):
    """QueryDictField is a generic textfield that neatly serializes/unserializes
    QueryDict objects to query string (GET parameters) seamlessly"""

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        """Convert our string value to a query string after we load it 
        from the DB"""
        if isinstance(value, basestring):
            return QueryDict(value, mutable=True)
        elif isinstance(value, QueryDict):
            # already converted
            return value

    def get_db_prep_save(self, value, connection=None):
        """Convert our QueryDict object to a query string before we save"""

        if value == "":
            return None

        if isinstance(value, QueryDict):
            value = value.urlencode()

        return super(QueryDictField, self).get_db_prep_save(value, connection=connection)

    def value_to_string(self, obj):
        """
        Prep value for serialization: same as prep for DB
        """
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_save(value)


# from http://south.aeracode.org/wiki/MyFieldsDontWork
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^querydictfield\.QueryDictField"])


