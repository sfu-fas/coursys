# from http://paltman.com/2010/feb/25/how-to-store-arbitrary-data-in-a-django-model/

from django.db import models
#from django.utils import simplejson as json
import json
from django.conf import settings
from datetime import datetime

class JSONEncoder(json.JSONEncoder):
   def default(self, obj):
       if isinstance(obj, datetime):
           return obj.strftime('%Y-%m-%d %H:%M:%S')
       elif isinstance(obj, datetime.date):
           return obj.strftime('%Y-%m-%d')
       elif isinstance(obj, datetime.time):
           return obj.strftime('%H:%M:%S')
       return json.JSONEncoder.default(self, obj)


class JSONField(models.TextField):
   def _dumps(self, data):
       return JSONEncoder().encode(data)

   def _loads(self, str):
       return json.loads(str, encoding=settings.DEFAULT_CHARSET)

   def db_type(self):
       return 'text'

   def pre_save(self, model_instance, add):
       value = getattr(model_instance, self.attname, None)
       return self._dumps(value)

   def contribute_to_class(self, cls, name):
       self.class_name = cls
       super(JSONField, self).contribute_to_class(cls, name)
       models.signals.post_init.connect(self.post_init)

       def get_json(model_instance):
           return self._dumps(getattr(model_instance, self.attname, None))
       setattr(cls, 'get_%s_json' % self.name, get_json)

       def set_json(model_instance, json):
           return setattr(model_instance, self.attname, self._loads(json))
       setattr(cls, 'set_%s_json' % self.name, set_json)

   def post_init(self, **kwargs):
       if 'sender' in kwargs and 'instance' in kwargs:
           if kwargs['sender'] == self.class_name and hasattr(kwargs['instance'], self.attname):
               value = self.value_from_object(kwargs['instance'])
               if (value):
                   setattr(kwargs['instance'], self.attname, self._loads(value))
               else:
                   setattr(kwargs['instance'], self.attname, None)


# from http://south.aeracode.org/wiki/MyFieldsDontWork
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^jsonfield\.JSONField"])


