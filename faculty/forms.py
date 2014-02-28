from django import forms
from django.forms.models import modelformset_factory
from django.template import Template, TemplateSyntaxError

from coredata.models import Unit

from models import CareerEvent
from models import DocumentAttachment
from models import MemoTemplate
from models import Memo
from models import EVENT_TYPE_CHOICES
from faculty.event_types.fields import SemesterField


def career_event_factory(person, post_data=None, post_files=None):
    if post_data:
        return CareerEventForm(post_data, post_files)
    return CareerEventForm(initial={"person": person})

class CareerEventForm(forms.ModelForm):
    class Meta:
        model = CareerEvent
        # TODO flags field throws 'int not iterable' error maybe to do with BitField?
        exclude = ("config", "flags", "person",)


class ApprovalForm(forms.ModelForm):
    class Meta:
        model = CareerEvent
        fields = ("status",)


class GetSalaryForm(forms.Form):
    date = forms.DateField();


def attachment_formset_factory():
    return modelformset_factory(DocumentAttachment, form=AttachmentForm, extra=1)


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = DocumentAttachment
        exclude = ("career_event", "created_by")


class MemoTemplateForm(forms.ModelForm):
    class Meta:
        model = MemoTemplate
        exclude = ('created_by', 'event_type', 'hidden')

    def __init__(self, *args, **kwargs):
        super(MemoTemplateForm, self).__init__(*args, **kwargs)
        self.fields['subject'].widget.attrs['size'] = 50
        self.fields['template_text'].widget.attrs['rows'] = 20
        self.fields['template_text'].widget.attrs['cols'] = 50

    def clean_template_text(self):
        template_text = self.cleaned_data['template_text']
        try:
            Template(template_text)
        except TemplateSyntaxError as e:
            raise forms.ValidationError('Syntax error in template: ' + unicode(e))
        return template_text

class MemoForm(forms.ModelForm):
    #use_sig = forms.BooleanField(initial=True, required=False, label="Use signature",
    #                             help_text='Use the "From" person\'s signature, if on file?')
    class Meta: 
        model = Memo
        exclude = ('unit', 'from_person', 'created_by', 'config', 'template', 'career_event', 'hidden')

        widgets = {
                   'career_event': forms.HiddenInput(),
                   'to_lines': forms.TextInput(attrs={'size': 50}),
                   'from_lines': forms.TextInput(attrs={'size': 50}),
                   'memo_text': forms.Textarea(attrs={'rows':25, 'cols': 70}),
                   'subject': forms.Textarea(attrs={'rows':2, 'cols':70}),
                   'cc_lines': forms.Textarea(attrs={'rows':3, 'cols':50}),
                   }

    def __init__(self,*args, **kwargs):
        super(MemoForm, self).__init__(*args, **kwargs)
        # reorder the fields to the order of the printed memo
        keys = ['to_lines', 'from_lines', 'subject', 'sent_date', 'memo_text', 'cc_lines']
        keys.extend([k for k in self.fields.keyOrder if k not in keys])
        self.fields.keyOrder = keys

    #def clean_use_sig(self):
    #    use_sig = self.cleaned_data['use_sig']
    #    self.instance.config['use_sig'] = use_sig
    #    return use_sig


class SearchForm(forms.Form):

    start_date = forms.DateField(label='Start Date', required=False)
    end_date = forms.DateField(label='End Date (inclusive)', required=False)
    unit = forms.ModelChoiceField(queryset=Unit.objects.all(), required=False)
