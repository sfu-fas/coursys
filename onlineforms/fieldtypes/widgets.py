from django import forms

class CustomMultipleInputWidget(forms.MultiWidget):
    NUM = 3 # get from attrs

    def __init__(self, attrs=None ):
        if attrs is not None:
            print "attrs!"
        else:
            print "no attrs :("

        widgets = [forms.TextInput(attrs=attrs)] * self.NUM

        super(CustomMultipleInputWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return '%s' % value
        return [None] * self.NUM

    def format_output(self, rendered_widgets):
        return u'</br>'.join(rendered_widgets)

    def render(self, name, value, attrs=None):
        name = str(name)
        output = super(CustomMultipleInputWidget, self).render(name, value, attrs)
        return output
