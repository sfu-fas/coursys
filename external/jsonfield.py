# from http://djangosnippets.org/snippets/1478/

from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
#from django.utils import simplejson as json
import json

class JSONField(models.TextField):
    """JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly"""

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB
        
        Stricter version to fail faster.
        """
        if value == "":
            return {}
        elif isinstance(value, basestring):
            return json.loads(value)
        elif isinstance(value, dict):
            # already converted
            return value

    def to_python_sloppy(self, value):
        """Convert our string value to JSON after we load it from the DB"""

        if value == "":
            return None

        try:
            if isinstance(value, basestring):
                return json.loads(value)
        except ValueError:
            pass

        return value

    def get_db_prep_save(self, value, connection=None):
        """Convert our JSON object to a string before we save"""

        if value == "":
            return None

        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)

        return super(JSONField, self).get_db_prep_save(value, connection=connection)


# from http://south.aeracode.org/wiki/MyFieldsDontWork
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^jsonfield\.JSONField"])


