# base models for FieldType classes

class FieldType(object):
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

