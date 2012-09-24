# base models for FieldType classes

class FieldType(object):
    def edit_form_factory(self):
        """
        Returns a Django Form/Field instance that can be used to edit this
        field's details.
        
        e.g. user might want to edit the things in the .config field:
        this Form lets them.
        """
        raise NotImplementedError
        
    def dispay_widget(self, filled=None):
        """
        Returns HTML for this field, to be filled in by the user. Should
        include the value from the filled object as an initial value (if
        given).
        
        e.g. an <input /> tag
        """
        raise NotImplementedError

    def display_value(self, filled):
        """
        Returns HTML for this field and filled-in value, to be displaye
        to the user.
        
        e.g. a <p> with the contents.
        """
        raise NotImplementedError

    def is_complete(self, filled):
        """
        Returns True if the filled-in value is "complete". i.e. if this
        field is required, is it "done"?
        """
        return filled.is_complete()
    
    def to_json(self, filled):
        """
        Convert filled field to JSON for storage
        """
        raise NotImplementedError
