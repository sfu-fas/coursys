from django import forms

class CustomMultipleInputWidget(forms.MultiWidget):

    def __init__(self, attrs=None ):
        if attrs is not None:
            self.num_inputs = attrs['max_responses']
        else:
            self.num_inputs = 3

        widgets = [forms.TextInput(attrs=attrs)] * int(self.num_inputs)

        super(CustomMultipleInputWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        #Take the single string and seperate them for each field.
        if value:
            return value.split("|")
        return [None] * int(self.num_inputs)

    def format_output(self, rendered_widgets):
        return u'</br>'.join(rendered_widgets)

    def render(self, name, value, attrs=None):
        name = str(name)
        output = super(CustomMultipleInputWidget, self).render(name, value, attrs)
        return output
