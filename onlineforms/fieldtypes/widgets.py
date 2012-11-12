from django import forms
#from django.forms import widgets
from django.utils.safestring import mark_safe

class CustomMultipleInputWidget(forms.MultiWidget):

    WIDGET_JAVASCRIPT = """
    <script type="text/javascript">
    $('document').ready(function () {
       alert('%(max)s')
    });
    </script>
    """

    def __init__(self, attrs=None, max=5, min=1 ):
        self.max=max
        widgets = [forms.TextInput() for _ in xrange(int(max))]

        super(CustomMultipleInputWidget, self).__init__(widgets, attrs=attrs)

    def decompress(self, value):
        if value:
            return value
            #return value.split("|")
        return [None] * int(self.max)

    def format_output(self, rendered_widgets):
        return u'</br>'.join(rendered_widgets) + mark_safe(self.WIDGET_JAVASCRIPT) % {'max': self.max}

    def render(self, name, value, attrs=None):
        name = str(name)
        output = super(CustomMultipleInputWidget, self).render(name, value, attrs)

        return output
