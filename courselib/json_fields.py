import copy


# tool to create convenient getters and setters for .config fields
def getter_setter(field):
    def getter(self):
        return self.config[field] if field in self.config else copy.copy(self.defaults[field])

    def setter(self, val):
        self.config[field] = val
    return getter, setter


# better version of getter_setter
def config_property(field, default):
    def getter(self):
        return self.config[field] if field in self.config else copy.copy(default)

    def setter(self, val):
        self.config[field] = val
    return property(getter, setter)


from jsonfield.fields import JSONField as JSONFieldOriginal
import json

class JSONField(JSONFieldOriginal):
    """
    override to allow null JSON to map to {}
    """
    def pre_init(self, value, obj):
        if value is None or value == '':
            return {}
        res = super(JSONField, self).pre_init(value, obj)
        # hack around https://github.com/bradjasper/django-jsonfield/issues/106 until fixed properly
        if isinstance(res, basestring):
            return json.loads(res)
        return res

#from south.modelsinspector import add_introspection_rules
#add_introspection_rules([], ["^courselib\.json_fields\.JSONField$"])
