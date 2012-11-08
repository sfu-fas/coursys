from django import forms
#from django.forms import widgets

class CustomMultipleInputWidget(forms.MultiWidget):

    WIDGET_JAVASCRIPT = """
    <script type="text/javascript">
    $('document').ready(function () {
       //Something here to add/remove options
    });
    </script>
    """


    def __init__(self, attrs=None, max=5, min=1 ):
        self.max=max
        widgets = []
        [widgets.append(forms.TextInput) for _ in xrange(int(max))]
        widgets = tuple(widgets)

        print widgets

        super(CustomMultipleInputWidget, self).__init__(widgets, attrs=attrs)

    def decompress(self, value):
        #Take the single string and seperate them for each field.
        print "DECOMPRESS"
        print value
        if value:
            return value.split("|")
        return [None] * int(self.max)

    def format_output(self, rendered_widgets):
        return u'</br>'.join(rendered_widgets)

    def render(self, name, value, attrs=None):
        name = str(name)
        output = super(CustomMultipleInputWidget, self).render(name, value, attrs)

        return output
