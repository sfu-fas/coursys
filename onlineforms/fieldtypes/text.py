from onlineforms.fieldtypes.base import FieldBase, FieldConfigForm
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape
from django.template.defaultfilters import linebreaksbr
from courselib.markup import MarkupContentField, markup_to_html


class SmallTextField(FieldBase):
    more_default_config = {'min_length': 1, 'max_length': 100}
    
    class SmallTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=100, initial=1, widget=forms.TextInput(attrs={'size': 3}))
        max_length = forms.IntegerField(min_value=1, max_value=100, initial=100, widget=forms.TextInput(attrs={'size': 3}))
        def clean(self):
            try:
                min_r = int(self.data['min_length'])
                max_r = int(self.data['max_length'])
                if min_r > max_r:
                    raise forms.ValidationError("Minimum length cannot be more than the maximum.")
            except (ValueError, KeyError):
                pass # let somebody else worry about that

            return super(self.__class__, self).clean()

    def make_config_form(self):
        return self.SmallTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        self.min_length = 0
        self.max_length = 0

        if self.config['min_length'] and int(self.config['min_length']) > 0:
            self.min_length = int(self.config['min_length'])
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            self.max_length = int(self.config['max_length'])

        c = forms.CharField(required=self.config['required'],
            widget=forms.TextInput(attrs=
                {'size': min(self.config.get('size', 60), int(self.config['max_length'])),
                 'maxlength': int(self.config['max_length'])}),
            label=self.config['label'],
            help_text=self.config['help_text'],
            min_length=self.min_length,
            max_length=self.max_length)

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + linebreaksbr(fieldsubmission.data['info'], autoescape=True) + '</p>')

    def to_text(self, fieldsubmission):
        return fieldsubmission.data['info']


class MediumTextField(FieldBase):
    more_default_config = {'min_length': 1, 'max_length': 1000}

    class MediumTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=1000, initial=1, widget=forms.TextInput(attrs={'size': 4}))
        max_length = forms.IntegerField(min_value=1, max_value=1000, initial=1000, widget=forms.TextInput(attrs={'size': 4}))
        def clean(self):
            try:
                min_r = int(self.data['min_length'])
                max_r = int(self.data['max_length'])
                if min_r > max_r:
                    raise forms.ValidationError("Minimum length cannot be more than the maximum.")
            except (ValueError, KeyError):
                pass # let somebody else worry about that

            return super(self.__class__, self).clean()

    def make_config_form(self):
        return self.MediumTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        self.min_length = 0
        self.max_length = 0

        if self.config['min_length'] and int(self.config['min_length']) > 0:
            self.min_length = int(self.config['min_length'])
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            self.max_length = int(self.config['max_length'])

        c = forms.CharField(required=self.config['required'],
            widget=forms.Textarea(attrs={'cols': '60', 'rows': self.config.get('rows', '3')}),
            label=self.config['label'],
            help_text=self.config['help_text'],
            min_length=self.min_length,
            max_length=self.max_length)

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + linebreaksbr(fieldsubmission.data['info'], autoescape=True) + '</p>')

    def to_text(self, fieldsubmission):
        return fieldsubmission.data['info']


class LargeTextField(FieldBase):
    more_default_config = {'min_length': 1, 'max_length': 10000}

    class LargeTextConfigForm(FieldConfigForm):
        min_length = forms.IntegerField(min_value=1, max_value=10000, initial=1, widget=forms.TextInput(attrs={'size': 5}))
        max_length = forms.IntegerField(min_value=1, max_value=10000, initial=10000, widget=forms.TextInput(attrs={'size': 5}))
        def clean(self):
            try:
                min_r = int(self.data['min_length'])
                max_r = int(self.data['max_length'])
                if min_r > max_r:
                    raise forms.ValidationError("Minimum length cannot be more than the maximum.")
            except (ValueError, KeyError):
                pass # let somebody else worry about that

            return super(self.__class__, self).clean()

    def make_config_form(self):
        return self.LargeTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):

        self.min_length = 0
        self.max_length = 0

        if self.config['min_length'] and int(self.config['min_length']) > 0:
            self.min_length = int(self.config['min_length'])
        if self.config['max_length'] and int(self.config['max_length']) > 0:
            self.max_length = int(self.config['max_length'])

        c = forms.CharField(required=self.config['required'],
            widget=forms.Textarea(attrs={'cols': '60', 'rows': self.config.get('rows', '15')}),
            label=self.config['label'],
            help_text=self.config['help_text'],
            min_length=self.min_length,
            max_length=self.max_length)

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + linebreaksbr(fieldsubmission.data['info'], autoescape=True) + '</p>')

    def to_text(self, fieldsubmission):
        return fieldsubmission.data['info']


class EmailTextField(FieldBase):
    class EmailTextConfigForm(FieldConfigForm):
        pass

    def make_config_form(self):
        return self.EmailTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        c = forms.EmailField(required=self.config['required'],
            label=self.config['label'],
            help_text=self.config['help_text'])

        if fieldsubmission:
            c.initial = fieldsubmission.data['info']

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        return mark_safe('<p>' + escape(self.to_text(fieldsubmission)) + '</p>')

    def to_text(self, fieldsubmission):
        return fieldsubmission.data['info']


class _ExplanationFieldWidget(forms.Textarea):
    """
    A non-widget widget that generates explanation text and not a form input.
    """
    def __init__(self, explanation, markup, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.explanation = explanation
        self.markup = markup

    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe('<div class="explanation_block">%s</div>' % (markup_to_html(self.explanation, self.markup)))


class ExplanationTextField(FieldBase):
    in_summary = False
    class ExplanationTextConfigForm(FieldConfigForm):
        text_explanation = MarkupContentField(with_wysiwyg=True, allow_math=False, help_text='Text to display to the user.')

        def __init__(self, config, *args, **kwargs):
            super(self.__class__, self).__init__(config, *args, **kwargs)
            del self.fields['help_text']
            # handle transition to markup-with-language-choice field
            if config and 'text_explanation' in config and 'text_explanation_0' not in config:
                config['text_explanation_0'] = config['text_explanation']
                config['text_explanation_1'] = 'creole'

    def make_config_form(self):
        return self.ExplanationTextConfigForm(self.config)

    def make_entry_field(self, fieldsubmission=None):
        # before MarkupContentField, text_explanation held the contents; now text_explanation_0.
        explanation = self.config.get('text_explanation_0', self.config.get('text_explanation', ''))
        markup = self.config.get('text_explanation_1', 'creole')

        w = _ExplanationFieldWidget(explanation=explanation, markup=markup,
                                    attrs={'class': 'disabled', 'readonly': 'readonly'})
        c = forms.CharField(required=False,
            label=self.config['label'],
            help_text='',
            widget=w)

        return c

    def serialize_field(self, cleaned_data):
        return {'info': cleaned_data}

    def to_html(self, fieldsubmission=None):
        # before MarkupContentField, text_explanation held the contents; now text_explanation_0.
        explanation = self.config.get('text_explanation_0', self.config.get('text_explanation', ''))
        markup = self.config.get('text_explanation_1', 'creole')
        return mark_safe('<div class="explanation_block">%s</div>' % (markup_to_html(explanation, markup)))

