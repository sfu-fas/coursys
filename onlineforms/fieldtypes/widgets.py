from django import forms
from django.utils.html import conditional_escape, mark_safe

class CustomMultipleInputWidget(forms.MultiWidget):
    initial_data = None

    def __init__(self, attrs=None, max=20, min=1 ):
        self.max = int(max)
        self.min = int(min)

        widgets = [forms.TextInput() for _ in range(self.max)]

        super(CustomMultipleInputWidget, self).__init__(widgets, attrs=attrs)

    def set_initial_data(self, value):
        self.initial_data = value

    def decompress(self, value):
        if self.initial_data:
            return self.initial_data
        return [None] * int(self.max)

    def render(self, name, value, attrs=None, renderer=None):
        output = super(CustomMultipleInputWidget, self).render(str(name), value, attrs=attrs, renderer=renderer)
        open_tag = '<div class="list-input" data-name="%s" data-min="%i" data-max="%i">' % (name, self.min, self.max)
        return mark_safe(open_tag) + conditional_escape(output) + mark_safe('</div>')
