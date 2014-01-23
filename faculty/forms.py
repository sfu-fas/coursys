from django import forms
#from django.forms.models import imlineformset_factory


from models import DocumentAttachment


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = DocumentAttachment 


class MemoTemplateForm(ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={'rows':'35', 'cols': '60'}))
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

class MemoForm(ModelForm):
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
