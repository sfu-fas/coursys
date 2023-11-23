from django import forms


METHOD_CHOICES = [
    ('', '\u2014'),
    ('GET', 'GET'),
    ('POST', 'POST'),
]


class RequestLogForm(forms.Form):
    method = forms.ChoiceField(choices=METHOD_CHOICES)

    def __init__(self, *args, **kwargs):
        super(RequestLogForm, self).__init__(*args, **kwargs)


class CeleryTaskForm(forms.Form):
    pass


# dict of forms for discovery in log exploration UI
EVENT_FORM_TYPES = {
    'request': RequestLogForm,
    'task': CeleryTaskForm,
}
