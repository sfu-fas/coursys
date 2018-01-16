from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.conf import settings
from django import forms
from django.forms import fields
from django.utils.html import conditional_escape as escape
from django.template import defaultfilters
from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from onlineforms.fieldtypes.widgets import CustomMultipleInputWidget
from coredata.models import Semester
import datetime, os

class CustomMultipleInputField(fields.MultiValueField):
    def __init__(self, name="", max=20, min=2, other_required=False, *args, **kwargs):
        self.min = min
        self.max = max
        self.required = other_required
        kwargs['widget'] = CustomMultipleInputWidget(name=name, max=max, min=min)
        self.field_set = [fields.CharField() for _ in range(int(max))]

        super(CustomMultipleInputField, self).__init__(fields=self.field_set, *args, **kwargs)


    def compress(self, data_list):
        if data_list:
            name = list(data_list.items())[1][0][0]
            count = 0
            data = []

            for k, v in sorted(iter(data_list.items()), key=lambda k_v: (k_v[0],k_v[1])):
                if str(k).startswith(str(name) + '_'):
                    if len(str(v)) > 0:
                        data.append(v)
                        count += 1

            if self.required and count < int(self.min):
                raise ValidationError('Enter at least '+self.min+' responses')

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
                    raise forms.ValidationError("Minimum number of responses cannot be more than the maximum.")
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

    def to_text(self, fieldsubmission=None):
        infos = fieldsubmission.data['info']
        return '; '.join(infos)


class _ClearableFileInput(forms.ClearableFileInput):
    template_with_initial = '<div class="formfileinput">Current file: %(initial)s %(clear_template)s<br />Upload file: %(input)s</div>'
    template_with_clear = '<br /><label class="sublabel" for="%(clear_checkbox_id)s">Remove current file:</label> %(clear)s'

    def render(self, name, value, attrs=None):
        name = str(name)
        substitutions = {
            'initial_text': self.initial_text,
            'input_text': self.input_text,
            'clear_template': '',
            'clear_checkbox_label': self.clear_checkbox_label,
        }
        template = '%(input)s'
        substitutions['input'] = super(forms.ClearableFileInput, self).render(name, value, attrs)

        if value and hasattr(value, "url"):
            template = self.template_with_initial
            substitutions['initial'] = ('<a href="%s">%s</a>'
                                        % (escape(value.file_sub.get_file_url()),
                                           escape(value.file_sub.display_filename())))
            if not self.is_required:
                checkbox_name = self.clear_checkbox_name(name)
                checkbox_id = self.clear_checkbox_id(checkbox_name)
                substitutions['clear_checkbox_name'] = escape(checkbox_name)
                substitutions['clear_checkbox_id'] = escape(checkbox_id)
                substitutions['clear'] = forms.CheckboxInput().render(checkbox_name, False, attrs={'id': checkbox_id})
                substitutions['clear_template'] = self.template_with_clear % substitutions

        return mark_safe(template % substitutions)




class FileCustomField(FieldBase):
    in_summary = False
    class FileConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        return self.FileConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        f = forms.FileField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'],
            widget=_ClearableFileInput())
        f.filesub = None
        if fieldsubmission:
            file_sub = fieldsubmission.file_sub()
            if file_sub:
                f.filesub = file_sub
                f.initial = file_sub.file_attachment
                f.initial.file_sub = fieldsubmission.file_sub()
        return f

    def serialize_field(self, cleaned_data):
        return {} # creation of FieldSubmissionFile handed in the view code

    def to_html(self, fieldsubmission=None):
        file_sub = fieldsubmission.file_sub()
        if file_sub:
            return mark_safe('<p>Uploaded file <a href="%s">%s</a></p>'
                             % (escape(file_sub.get_file_url()),
                                escape(file_sub.display_filename())))
        else:
            return mark_safe('<p class="empty">No file submitted.</p>')


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
        return mark_safe('<p>' + escape(self.to_text(fieldsubmission)) + '</p>')

    def to_text(self, fieldsubmission=None):
        return fieldsubmission.data['info']


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
        current = Semester.current()
        # always limit to 10 years on either side of today: that seems like a reasonable window
        queryset = Semester.objects \
            .filter(name__gte=current.offset_name(-30), name__lte=current.offset_name(30)) \
            .order_by('name')
        allowed = self.config.get('allowed_semesters', 'AL')
        if allowed == 'AL':
            initial = current.name
        elif allowed == 'LT':
            queryset = queryset.filter(name__lt=current.name).order_by('-name')
            initial = current.offset_name(-1)
        elif allowed == 'LE':
            queryset = queryset.filter(name__lte=current.name).order_by('-name')
            initial = current.name
        elif allowed == 'GT':
            queryset = queryset.filter(name__gt=current.name)
            initial = current.offset_name(1)
        elif allowed == 'GE':
            queryset = queryset.filter(name__gte=current.name)
            initial = current.name

        the_choices = [(s.name, s.label()) for s in queryset]

        widget = forms.Select
        if self.config.get('format', 'D') == 'R':
            widget = forms.RadioSelect

        required = self.config['required']
        if not required:
            initial = None

        c = forms.ChoiceField(required=required,
            label=self.config['label'],
            help_text=self.config['help_text'],
            choices=the_choices,
            widget=widget,
            initial=initial)

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        if not self.config['required']:
            c.choices.insert(0, ('', '\u2014'))

        return c

    def serialize_field(self,  cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(self.to_text(fieldsubmission)) + '</p>')

    def to_text(self, fieldsubmission=None):
        return fieldsubmission.data['info']


ALLOWED_DATE_CHOICES = [
        ('AL', 'Any date'),
        ('LT', 'Days in the past'),
        ('LE', 'Days in the past (including the current date)'),
        ('GT', 'Days in the future'),
        ('GE', 'Days in the future (including the current date)'),
        ]
class DateSelectField(FieldBase):
    class DateConfigForm(FieldConfigForm):
        allowed_dates = forms.ChoiceField(choices=ALLOWED_DATE_CHOICES, initial='AL',
                widget=forms.RadioSelect,
                help_text='Which semesters should it be possible to choose?')

    def make_config_form(self):
        return self.DateConfigForm(self.config)

    def _validator(self, value):
        """
        Validate the allowed_dates restrictions on the field.
        """
        allowed = self.config.get('allowed_dates', 'AL')
        today = datetime.date.today()
        if allowed == 'AL':
            pass
        elif allowed == 'LT' and value >= today:
            raise forms.ValidationError("The date must be before today.")
        elif allowed == 'LE' and value > today:
            raise forms.ValidationError("The date cannot be in the future.")
        elif allowed == 'GT' and value <= today:
            raise forms.ValidationError("The date must be after today.")
        elif allowed == 'GE' and value < today:
            raise forms.ValidationError("The date cannot be past.")
    
    def make_entry_field(self, fieldsubmission=None):
        c = forms.DateField(required=self.config['required'],
            label=self.config['label'],
            validators=[self._validator],
            help_text=self.config['help_text'])
        
        c.widget.attrs['class'] = 'date-input' # a JS chunk uses the class to turn on the datepicker.
        
        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(self._to_text(fieldsubmission)) + '</p>')

    def to_text(self, fieldsubmission=None):
        return self._to_text(fieldsubmission, 'Y-m-d')

    def _to_text(self, fieldsubmission=None, format=settings.DATE_FORMAT):
        if fieldsubmission.data['info']:
            d = datetime.datetime.strptime(fieldsubmission.data['info'], '%Y-%m-%d').date()
            return escape(defaultfilters.date(d, format))
        else:
            return 'not entered'


class DividerField(FieldBase):
    configurable = False
    in_summary = False

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
