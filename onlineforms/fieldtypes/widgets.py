from distutils.command.clean import clean
from django import forms
#from django.forms import widgets
from django.utils.safestring import mark_safe

class CustomMultipleInputWidget(forms.MultiWidget):
    WIDGET_JAVASCRIPT = """
    <script type="text/javascript">
    $('document').ready(function () {

        var scripts = document.getElementsByTagName( 'script' );
        var thisScriptTag = scripts[ scripts.length - 1 ];

        $(thisScriptTag).after('HELLO');
        $(thisScriptTag).closest('dl').after('<dt id="add_dt"><label for="add_button">Add</label></dt><dd>\ ' +
                        '<div class="field"><input type="button" name="Add Choice" value="Add Choice" id="add_button" /></div>\ ' +
                        '</dd>');
        //$("dd").last().after('<dt id="add_dt"><label for="add_button">Add</label></dt><dd>\ ' +
         //               '<div class="field"><input type="button" name="Add Choice" value="Add Choice" id="add_button" /></div>\ ' +
         //               '</dd>');
    });
    </script>
    """

    def __init__(self, attrs=None, name="test", max=20, min=1 ):
        self.max = max
        self.min = min
        self.name = name

        widgets = [forms.TextInput() for _ in xrange(int(self.max))]

        super(CustomMultipleInputWidget, self).__init__(widgets, attrs=attrs)

    def decompress(self, value):
        if value:
            return value
            #return value.split("|")
        return [None] * int(self.max)

    def format_output(self, rendered_widgets):
        output = rendered_widgets[0]
        for widget in rendered_widgets[1:]:
            output += u'<dt style="visibility:hidden"> <label>{0}</label></dt><dd><div class="field">{1}<br/></div</dd>'.format(self.name, widget)
        output += mark_safe(self.WIDGET_JAVASCRIPT) % {'max': self.max, 'min': self.min}
        return output

    def render(self, name, value, attrs=None):
        name = str(name)
        output = super(CustomMultipleInputWidget, self).render(name, value, attrs)

        return output
