from django import forms


METHOD_CHOICES = [
    ('', '\u2014'),
    ('GET', 'GET'),
    ('POST', 'POST'),
]
BOOLEAN_FILTER_CHOICES = [
    ('', '\u2014'),
    ('YES', 'Yes'),
    ('NO', 'No'),
]


class EventLogFilterForm(forms.Form):
    duration = forms.FloatField(label='Duration (s) ≥ ')
    duration.widget.attrs.update(size="4")

    def bound_fields(self):
        # hack to let us discover the bound-fields in the template.
        for ident in self.fields:
            yield self[ident]


class RequestLogForm(EventLogFilterForm):
    method = forms.ChoiceField(choices=METHOD_CHOICES)
    username = forms.CharField()
    path = forms.CharField(label='Path contains')
    ip = forms.CharField(label='IP address')
    session_key = forms.CharField()
    status_code = forms.IntegerField()
    view_name = forms.CharField(label='View name contains')

    username.widget.attrs.update(size="8")
    path.widget.attrs.update(size="20")
    ip.widget.attrs.update(size="15")
    session_key.widget.attrs.update(size="20")
    status_code.widget.attrs.update(size="4")
    view_name.widget.attrs.update(size="15")


class CeleryTaskForm(EventLogFilterForm):
    task = forms.CharField(label='Task contains')
    exception = forms.ChoiceField(choices=BOOLEAN_FILTER_CHOICES)

    task.widget.attrs.update(size="15")

# dict of forms for discovery in log exploration UI
EVENT_FORM_TYPES = {
    'request': RequestLogForm,
    'task': CeleryTaskForm,
}
