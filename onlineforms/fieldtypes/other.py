from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms
from django.forms import fields
from onlineforms.fieldtypes.widgets import CustomMultipleInputWidget
from coredata.models import Semester

class CustomMultipleInputField(fields.MultiValueField):
    def __init__(self, name="", max=20, min=2, other_required=False, *args, **kwargs):
        self.min = min
        self.max = max
        self.required = other_required
        kwargs['widget'] = CustomMultipleInputWidget(name=name, max=max, min=min)
        self.field_set = [fields.CharField() for _ in xrange(int(max))]

        super(CustomMultipleInputField, self).__init__(fields=self.field_set, *args, **kwargs)


    def compress(self, data_list):
        if data_list:
            name = data_list.items()[1][0][0]
            count = 0
            data = []

            for k, v in sorted(data_list.iteritems(), key=lambda (k,v): (k,v)):
                if str(k).startswith(str(name) + '_'):
                    if len(str(v)) > 0:
                        data.append(v)
                        count += 1

            if self.required and count < int(self.min):
                raise ValidationError, 'Enter at least '+self.min+' responses'

            return data
        return None


class ListField(FieldBase):
    more_default_config = {'min_responses': 2, 'max_responses': 5}

    class ListConfigForm(FieldConfigForm):
        min_responses = forms.IntegerField(min_value=1, max_value=20, initial=2, widget=forms.TextInput(attrs={'size': 2}))
        max_responses = forms.IntegerField(min_value=1, max_value=20, initial=5, widget=forms.TextInput(attrs={'size': 2}))
        def clean(self):
            try:
                min_r = int(self.data['min_responses'])
                max_r = int(self.data['max_responses'])
                if min_r > max_r:
                    raise forms.ValidationError, "Minimum number of responses cannot be more than the maximum."
            except (ValueError, KeyError):
                pass # let somebody else worry about that

            return super(self.__class__, self).clean()


    def make_config_form(self):
        return self.ListConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        return CustomMultipleInputField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'],
            min=self.config['min_responses'],
            max=self.config['max_responses'],
            name=self.config['label'],
            other_required=self.config['required'])


    def serialize_field(self, cleaned_data):
        return{'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        infos = fieldsubmission.data['info']
        html = '<ul>'
        for info in infos:
            html += '<li>' + info + '</li>'
        html += '</ul>'

        return mark_safe(html)


class FileCustomField(FieldBase):
    class FileConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        return self.FileConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        return forms.FileField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'])

    def serialize_field(self, cleaned_data):
        return {} # creation of FieldSubmissionFile handed in the view code

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + 'File title?' + '</p>')


class URLCustomField(FieldBase):
    class URLConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        return self.URLConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = forms.URLField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'])

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        return c

    def serialize_field(self,  cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + fieldsubmission.data['info'] + '</p>')


ALLOWED_SEMESTER_CHOICES = [
        ('AL', 'All semesters'),
        ('LT', 'Past semesters'),
        ('LE', 'Past semesters (or current semester)'),
        ('GT', 'Future semesters'),
        ('GE', 'Future semesters (or current semester)'),
        ]
class SemesterField(FieldBase):
    
    class SemesterConfigForm(FieldConfigForm):
        allowed_semesters = forms.ChoiceField(choices=ALLOWED_SEMESTER_CHOICES, initial='AL',
                widget=forms.RadioSelect,
                help_text='Which semesters should it be possible to choose?')
        format = forms.ChoiceField(initial='D', choices=[('R', 'Radio Buttons'), ('D', 'Dropdown list')],
                widget=forms.RadioSelect,
                help_text='How should the selection be displayed to the user?')

    def make_config_form(self):
        return self.SemesterConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        queryset = Semester.objects.all().order_by('name')
        allowed = self.config['allowed_semesters']
        current = Semester.current().name
        if allowed == 'AL':
            pass
        elif allowed == 'LT':
            queryset = queryset.filter(name__lt=current).order_by('-name')
        elif allowed == 'LE':
            queryset = queryset.filter(name__lte=current).order_by('-name')
        elif allowed == 'GT':
            queryset = queryset.filter(name__gt=current)
        elif allowed == 'GE':
            queryset = queryset.filter(name__gte=current)

        the_choices = [(s.name, s.label()) for s in queryset]

        widget = forms.Select
        if self.config['format'] == 'R':
            widget = forms.RadioSelect

        c = forms.ChoiceField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'],
            choices=the_choices,
            widget=widget,)


        if fieldsubmission:
            initial=fieldsubmission.data['info']
            c.initial=initial

        if not self.config['required']:
            c.choices.insert(0, ('', u'\u2014'))

        return c

    def serialize_field(self,  cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + fieldsubmission.data['info'] + '</p>')


class DividerField(FieldBase):
    configurable = False

    def make_config_form(self):
        return self.configurable

    def make_entry_field(self, fieldsubmission=None):
        from onlineforms.forms import DividerFieldWidget

        return forms.CharField(required=False,
            widget=DividerFieldWidget(),
            label='',
            help_text='')

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<hr />')
