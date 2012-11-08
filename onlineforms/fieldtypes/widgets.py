#from django import forms
from django.forms import widgets

class CustomMultipleInputWidget(widgets.MultiWidget):

    WIDGET_JAVASCRIPT = """
    <script type="text/javascript">
    $('document').ready(function () {
       //Something here to add/remove options
    });
    </script>
    """

    def __init__(self, attrs=None, max=5, min=1 ):
        self.max=max
        w_list = []
        [w_list.append(widgets.TextInput()) for _ in xrange(int(max))]
        w_list = tuple(w_list)

        super(CustomMultipleInputWidget, self).__init__(w_list, attrs)

    def decompress(self, value):
        #Take the single string and seperate them for each field.
        print "DECOMPRESS"
        print value
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
