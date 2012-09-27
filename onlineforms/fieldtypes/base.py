import json
# base models for FieldType classes

class FieldConfigForm( forms.Form ):
    """ 
    The base form for field configuration. 
    
    'required', 'label', and 'help_text' are implemented on 
    all field objects. 
    
    """
    required = forms.BooleanField( label="Required")
    label = forms.CharField( label="Label" )
    help_text = forms.CharField( label="Help Text" )

class FieldFactory( object ):

    def __init__(self, config):
        """
        Given a 'config' dictionary, instantiate this object in such
        a way that it will produce the Field object described by the
        dictionary. 
        """
        self.config = FieldFactory.deserialize_config(config)

    def make_field_config_form(self):
        """
        Returns a Django Form instance that can be used to edit this
        field's details.

        The Form's 'cleaned_data' should match this code's 'config'
        object. 
        
        e.g. user might want to edit the things in the .config field:
        this Form lets them.
        """
        raise NotImplementedError
        
    def make_entry_field(self):
        """
        Returns a Django Field for this field, to be filled in by the user. 
        
        e.g. a CharField field.
        """
        raise NotImplementedError
    
    def to_serializable(self, filled):
        """
        Convert filled field to a JSON-friendly format. 

        e.g., converting the result of a DateTimeField's 'clean()' method (which is
        itself a datetime) to an ISO standard serialization format 
        """
        return unicode(filled.clean())
