from distutils.command.clean import clean
from django import forms
#from django.forms import widgets
from django.utils.safestring import mark_safe

class CustomMultipleInputWidget(forms.MultiWidget):
    WIDGET_JAVASCRIPT = """
    <script type="text/javascript">
    $('document').ready(function () {

        var name = '%(max)s'

        min = typeof(min) == 'undefined' ? new Object() : min
        min[name.toString()] = '%(min)s'

        max = typeof(max) == 'undefined' ? new Object() : max
        max[name.toString()] = '%(max)s'

        current = typeof(current) == 'undefined' ? new Object() : current
        current[name.toString()] = parseInt(min[name.toString()])

        widget_dts = typeof(widget_dts) == 'undefined' ? new Object(): widget_dts
        widget_dds = typeof(widget_dds) == 'undefined' ? new Object(): widget_dds

        widget_dts[name.toString()] = []
        widget_dds[name.toString()] = []

        var scripts = document.getElementsByTagName( 'script' )
        var thisScriptTag = scripts[ scripts.length - 1 ]

        amount = typeof(amount) == 'undefined' ? new Object() : amount

        amount[name.toString()] = function () {
            var count = 0;
            for (var i = 0; i < max[name.toString()]; i++){
                if (widget_dds[name.toString()][i].is(':visible')){
                    count += 1;
                }
            }
            return count
        }

        cursor = $(thisScriptTag).parents('dd')

        for(var i=max[name.toString()]-1; i >= 0; i--){
            widget_dds[name.toString()][i] = cursor;
            cursor = $(cursor).prev()
            widget_dts[name.toString()][i] = cursor;
            cursor = $(cursor).prev()

            if(i-min[name.toString()] >= 0){
                if ($(widget_dds[name.toString()][i]).find('input').attr('value').length === 0){
                    widget_dds[name.toString()][i].hide();
                    widget_dts[name.toString()][i].hide();
                }
                else{
                    current[name.toString()] += 1
                }
            }
        }

        $(widget_dts[name.toString()][max[name.toString()]-1]).after('<dt><label>Add</label></dt><dd class="add_button">\ ' +
                        '<div class="field"><input type="button" name="Add Choice" value="Add Response" class="button" /></div>\ ' +
                        '</dd>');

        add_button = $(widget_dts[name.toString()][max[name.toString()]-1]).next().next().find('input')

        $(add_button).click(function () {
            if(current[name.toString()] < max[name.toString()]){
                widget_dts[name.toString()][current[name.toString()]].show()
                widget_dds[name.toString()][current[name.toString()]].show()
                current[name.toString()] += 1
            }

            if (amount[name.toString()]() >= max[name.toString()]){
                $(add_button).parents('.add_button').prev().hide()
                $(add_button).parents('.add_button').hide()
            }
        });
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
        return [None] * int(self.max)

    def format_output(self, rendered_widgets):
        output = rendered_widgets[0]
        for widget in rendered_widgets[1:]:
            output += u'<dt style="visibility:hidden"> <label>{0}</label></dt><dd><div class="field">{1}</div</dd>'.format(
                self.name, widget)
        output += mark_safe(self.WIDGET_JAVASCRIPT) % {'max': self.max, 'min': self.min, 'name': self.name}
        return output

    def render(self, name, value, attrs=None):
        name = str(name)
        output = super(CustomMultipleInputWidget, self).render(name, value, attrs)

        return output
