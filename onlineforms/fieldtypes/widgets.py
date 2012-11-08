from django import forms

class CustomMultipleInputWidget(forms.MultiWidget):

    def __init__(self, attrs=None, max=5, min=1 ):
        self.max=max

        #if attrs is not None:
        #    self.num_inputs = attrs['max_responses']
        #else:
        #    self.num_inputs = 3


        wanted_values = ['']
        widgets = [forms.TextInput(attrs=attrs)] * int(max)

        super(CustomMultipleInputWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        #Take the single string and seperate them for each field.
        print "DECOMPRESS"
        if value:
            return value.split("|")
        return [None] * int(self.max)

    def format_output(self, rendered_widgets):
        print "FORMAT OUTPUT"
        return u'</br>'.join(rendered_widgets)

    def render(self, name, value, attrs=None):
        print "RENDER"
        name = str(name)
        output = super(CustomMultipleInputWidget, self).render(name, value, attrs)
        return output
