from django import forms
from django.forms.models import modelformset_factory
from django.template import Template, TemplateSyntaxError

from models import CareerEvent
from models import DocumentAttachment
from models import MemoTemplate
from models import Memo



def career_event_factory(person, post_data=None, post_files=None):
    if post_data:
        return CareerEventForm(post_data, post_files)
    return CareerEventForm(initial={"person": person})

class CareerEventForm(forms.ModelForm):
    class Meta:
        model = CareerEvent
        # TODO flags field throws 'int not iterable' error maybe to do with BitField?
        exclude = ("config", "flags", "person",)


def attachment_formset_factory():
    return modelformset_factory(DocumentAttachment, form=AttachmentForm, extra=1)


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = DocumentAttachment
        exclude = ("career_event", "created_by")


class MemoTemplateForm(forms.ModelForm):
    template_text = forms.CharField(widget=forms.Textarea(attrs={'rows':'30', 'cols': '60'}))
    class Meta:
        model = MemoTemplate
        exclude = ('created_by',)
    
    def clean_content(self):
        content = self.cleaned_data['content']
        try:
            Template(content)
        except TemplateSyntaxError as e:
            raise forms.ValidationError('Syntax error in template: ' + unicode(e))
        return content

class MemoForm(forms.ModelForm):
    use_sig = forms.BooleanField(initial=True, required=False, label="Use signature",
                                 help_text='Use the "From" person\'s signature, if on file?')    
    class Meta: 
        model = Memo
        exclude = ('created_by', 'config', 'template')
        widgets = {
                   'career_event': forms.HiddenInput(),
                   'to_lines': forms.Textarea(attrs={'rows': 4, 'cols': 50}),
                   'from_lines': forms.Textarea(attrs={'rows': 3, 'cols': 30}),
                   'content': forms.Textarea(attrs={'rows':'25', 'cols': '70'}),
                   }
    
    def __init__(self, *args, **kwargs):
        super(MemoForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            self.initial['use_sig'] = kwargs['instance'].use_sig()
    
    def clean_use_sig(self):
        use_sig = self.cleaned_data['use_sig']
        self.instance.config['use_sig'] = use_sig
        return use_sig
