from coredata.forms import PersonField
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.fields import MultipleChoiceField
from django.forms.models import ModelForm
from onlineforms.models import Form, Sheet, FIELD_TYPE_CHOICES, FIELD_TYPE_MODELS, FormGroup, VIEWABLE_CHOICES, NonSFUFormFiller
from django.utils.safestring import mark_safe
from django.forms.utils import ErrorList

class DividerFieldWidget(forms.TextInput):
    def render(self, name, value, attrs=None):
        return mark_safe('<hr />')


# Manage groups
class GroupForm(ModelForm):
    class Meta:
        model = FormGroup
        exclude = ('members', 'config')

class EditGroupForm(ModelForm):
    class Meta:
        model = FormGroup
        fields = ('name',)

class EmployeeSearchForm(forms.Form):
    search = PersonField(label="Person")
    email = forms.BooleanField(required=False, initial=True,
            help_text="Should this member be emailed when submissions come in?")

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(EmployeeSearchForm, self).is_valid(*args, **kwargs)

# Manage forms
class FormForm(ModelForm):
    loginprompt = forms.BooleanField(required=False, initial=True, label='Login prompt',
                                     help_text='Should non-logged-in users be prompted to log in? Uncheck this if you '
                                               'expect most users to be external to SFU.')
    unlisted = forms.BooleanField(required=False, initial=False, label='Unlisted',
                                  help_text='Should this form be visible in the list of forms everyone can see?  '
                                            'if this is checked, only people with the direct URL will be able to '
                                            'fill in this form.')

    class Meta:
        model = Form
        exclude = ('active', 'original', 'unit', 'config')
        widgets = {
                'description': forms.TextInput(attrs={'size': '70'})
                }

    def __init__(self, *args, **kwargs):
        super(FormForm, self).__init__(*args, **kwargs)
        self.initial['loginprompt'] = self.instance.loginprompt()
        self.initial['unlisted'] = self.instance.unlisted()

    def save(self, *args, **kwargs):
        self.instance.set_loginprompt(self.cleaned_data['loginprompt'])
        self.instance.set_unlisted(self.cleaned_data['unlisted'])
        return super(FormForm, self).save(*args, **kwargs)

    # get instance of the FormForm    
    def _get(self):
            return self.instance
    #Validation error on assigning Forms without initial sheets         
    def clean_initiators(self):
        initiators = self.cleaned_data['initiators']
        form = self._get()
        if initiators != 'NON' and not Sheet.objects.filter(form=form, is_initial=True, active=True):
            raise forms.ValidationError, "Can't activate until you have created at least one sheet to be filled out."
        return initiators

class NewFormForm(FormForm):
    class Meta:
        model = Form
        exclude = ('active', 'original', 'unit', 'initiators', 'config')
        widgets = {
                'description': forms.TextInput(attrs={'size': '70'})
                }


class SheetForm(forms.Form):
    title = forms.CharField(required=True, max_length=30, label=mark_safe('Title'), help_text='Name of the sheet')
    can_view = forms.ChoiceField(required=True, choices=VIEWABLE_CHOICES, label='Can view', help_text='When someone is filling out this sheet, what else can they see?')

class EditSheetForm(ModelForm):
    class Meta:
        model = Sheet
        exclude = ('active', 'original', 'order', 'is_initial', 'config', 'form')

class NonSFUFormFillerForm(ModelForm):
    class Meta:
        model = NonSFUFormFiller
        exclude = ('config',)

class FieldForm(forms.Form):
    type = forms.ChoiceField(required=True, choices=FIELD_TYPE_CHOICES, label='Type')

# Administrate forms

class _FormModelChoiceField(forms.ModelChoiceField):
    widget = forms.RadioSelect
    def label_from_instance(self, obj):
        return obj.title

class _AdminAssignForm(forms.Form):
    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(_AdminAssignForm, self).is_valid(*args, **kwargs)

class AdminAssignFormForm(_AdminAssignForm):
    form = _FormModelChoiceField(required=True, queryset=Form.objects.none(), empty_label=None)
    assignee = PersonField(label='Assign to', required=True, needs_email=True)

    def __init__(self, query_set, *args, **kwargs):
        super(AdminAssignFormForm, self).__init__(*args, **kwargs)
        self.fields['form'].queryset = query_set

class AdminAssignSheetForm(_AdminAssignForm):
    sheet = _FormModelChoiceField(required=True, queryset=Sheet.objects.none(), empty_label=None)
    assignee = PersonField(label='Assign to', required=True, needs_email=True)
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'cols': '70'}),
            help_text="Optional comment on the form: this becomes part of the form history. If you have additional info about this submission, you can record it here.")
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'cols': '70'}),
            help_text="Optional private note to the assignee")

    def __init__(self, query_set, *args, **kwargs):
        super(_AdminAssignForm, self).__init__(*args, **kwargs)
        self.fields['sheet'].queryset = query_set

class _AdminAssignForm_nonsfu(ModelForm):
    class Meta:
        model = NonSFUFormFiller
        exclude = ('config',)

class AdminAssignFormForm_nonsfu(_AdminAssignForm_nonsfu):
    form = _FormModelChoiceField(required=True, queryset=Form.objects.none(), empty_label=None)

    def __init__(self, query_set, *args, **kwargs):
        super(_AdminAssignForm_nonsfu, self).__init__(*args, **kwargs)
        self.fields['form'].queryset = query_set

class AdminAssignSheetForm_nonsfu(_AdminAssignForm_nonsfu):
    sheet = _FormModelChoiceField(required=True, queryset=Sheet.objects.none(), empty_label=None)
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': '3', 'cols': '70'}),
            help_text="Optional comment on the form: this becomes part of the form history.")
    note = forms.CharField(required=False, widget=forms.TextInput(attrs={'size': '70'}),
            help_text="Optional note to the assignee")

    def __init__(self, query_set, *args, **kwargs):
        super(_AdminAssignForm_nonsfu, self).__init__(*args, **kwargs)
        self.fields['sheet'].queryset = query_set



class ChangeOwnerForm(forms.Form):
    new_group = forms.ModelChoiceField(queryset=None, required=True,
                    help_text="Form group that should take ownership of this form submission")
    def __init__(self, queryset, *args, **kwargs):
        super(ChangeOwnerForm, self).__init__(*args, **kwargs)
        self.fields['new_group'].queryset = queryset


class AdminReturnForm(forms.Form):
    reason = forms.CharField(required=True,
                help_text="Reason you are giving the form back: will be emailed to the user.",
                widget=forms.TextInput(attrs={'size': '70'}))


class CloseFormForm(forms.Form):
    summary = forms.CharField(required=True,
                help_text="Summary of the form, for advisors (and emailing to student if you select below).",
                widget=forms.Textarea(attrs={'rows': '5', 'cols': '70'})
                )
    email = forms.BooleanField(initial=False, required=False, help_text="Would you like to email the summary to the student?")
    
    def __init__(self, advisor_visible, *args, **kwargs):
        super(CloseFormForm, self).__init__(*args, **kwargs)
        self.used = True
        if not advisor_visible:
            # only care about these fields for advisor-visible things
            del self.fields['summary']
            del self.fields['email']
            self.used = False
            




class DynamicForm(forms.Form):
    def __init__(self, title, *args, **kwargs):
        self.title = title
        super(DynamicForm, self).__init__(*args, **kwargs)
        # Force no enforcing of required field by browser so we can save the form.
        self.use_required_attribute=False

    def fromFields(self, fields, field_submissions=[]):
        """
        Sets the fields from a list of field model objects
        preserving the order they are given in
        """
        # create a dictionary so you can find a fieldsubmission based on a field
        field_submission_dict = {}
        for field_submission in field_submissions:
            field_submission_dict[field_submission.field] = field_submission
        fieldargs = {}
        # keep a dictionary of the configured display fields, so we can serialize them with data later
        self.display_fields = {}
        for (counter, field) in enumerate(fields):
            # get the field
            display_field = FIELD_TYPE_MODELS[field.fieldtype](field.config)
            # make the form field, using the form submission data if it exists
            if field in field_submission_dict:
                self.fields[counter] = display_field.make_entry_field(field_submission_dict[field])
                if (field.fieldtype == "LIST"):
                    self.fields[counter].widget.set_initial_data(field_submission_dict[field].data['info'])
            else:
                self.fields[counter] = display_field.make_entry_field()
            # keep the display field for later
            self.display_fields[self.fields[counter] ] = display_field


    def fromPostData(self, post_data, files_data, ignore_required=False):
        self.cleaned_data = {}
        for name, field in self.fields.items():
            try:
                if isinstance(field, forms.MultiValueField):
                    relevant_data = dict([(k,v) for k,v in post_data.items() if k.startswith(str(name)+"_")])
                    relevant_data[str(name)] = u''
                    relevant_data['required'] = ignore_required
                    cleaned_data = field.compress(relevant_data)
                elif isinstance(field, forms.FileField):
                    if str(name) in files_data:
                        cleaned_data = field.clean(files_data[str(name)])
                    elif field.filesub:
                        # we have no new file, but an old file submission: fake it into place
                        fs = field.filesub
                        cleaned_data = SimpleUploadedFile(name=fs.file_attachment.name,
                                            content=fs.file_attachment.read(),
                                            content_type=fs.file_mediatype)
                    elif ignore_required:
                        cleaned_data = ""
                    else:
                        cleaned_data = field.clean("")
                elif str(name) in post_data:
                    if ignore_required and post_data[str(name)] == "":
                        cleaned_data = ""
                    else:
                        if isinstance(field, MultipleChoiceField):
                            relevant_data = post_data.getlist(str(name))
                            cleaned_data = field.clean(relevant_data)
                        else:
                            cleaned_data = field.clean(post_data[str(name)])
                else:
                    if ignore_required:
                        cleaned_data = ""
                    else:
                        cleaned_data = field.clean("")
                self.cleaned_data[str(name)] = cleaned_data
                field.initial = cleaned_data
            except forms.ValidationError, e:
                #self.errors[name] = ", ".join(e.messages)
                self.errors[name] = ErrorList(e.messages)
                if str(name) in post_data:
                    field.initial = post_data[str(name)]
                else:
                    initial_data = [v for k,v in post_data.items() if k.startswith(str(name)+"_") and v != '']
                    field.initial = initial_data

    def is_valid(self):
        # override because I'm not sure how to bind this form to data (i.e. form.is_bound)
        return not bool(self.errors)

    def validate(self, post):
        """
        Validate the contents of the form
        """
        for name, field in self.fields.items():
            try:
                field.clean(post[str(name)])
            except Exception, e:
                self.errors[name] = e.message
