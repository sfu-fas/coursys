from coredata.forms import PersonField
from django import forms
from django.forms.fields import MultipleChoiceField
from django.forms.models import ModelForm
from onlineforms.models import Form, Sheet, FIELD_TYPE_CHOICES, FIELD_TYPE_MODELS, FormGroup, VIEWABLE_CHOICES, NonSFUFormFiller
from django.utils.safestring import mark_safe
from pages.models import ParserFor

class DividerFieldWidget(forms.TextInput):
    def render(self, name, value, attrs=None):
        return mark_safe('<hr />')


class ExplanationFieldWidget(forms.Textarea):
    def render(self, name, value, attrs=None):
        parser = ParserFor(offering=None)
        return mark_safe('<div class="explanation_block">%s</div>' % parser.text2html(self.explanation))

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
    class Meta:
        model = Form
        exclude = ('active', 'original', 'unit', 'config')
        widgets = {
                'description': forms.TextInput(attrs={'size': '70'})
                }

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
class AdminAssignForm(forms.Form):
    class FormModelChoiceField(forms.ModelChoiceField):
        widget = forms.RadioSelect
        def label_from_instance(self, obj):
            return obj.title

    assignee = PersonField(label='Assign to', required=True)

    def __init__(self, label, query_set, *args, **kwargs):
        super(AdminAssignForm, self).__init__(*args, **kwargs)
        self.fields.insert(0, label, self.FormModelChoiceField(required=True,
            queryset=query_set,
            empty_label=None,
            label=label.capitalize()))

    def is_valid(self, *args, **kwargs):
        PersonField.person_data_prep(self)
        return super(AdminAssignForm, self).is_valid(*args, **kwargs)


class AdminAssignForm_nonsfu(ModelForm):
    class FormModelChoiceField(forms.ModelChoiceField):
        widget = forms.RadioSelect
        def label_from_instance(self, obj):
            return obj.title

    class Meta:
        model = NonSFUFormFiller
        exclude = ('config',)

    def __init__(self, label, query_set, *args, **kwargs):
        super(AdminAssignForm_nonsfu, self).__init__(*args, **kwargs)
        self.fields.insert(0, label, self.FormModelChoiceField(required=True,
            queryset=query_set,
            empty_label=None,
            label=label.capitalize()))

class ChangeOwnerForm(forms.Form):
    new_group = forms.ModelChoiceField(queryset=None, required=True,
                    help_text="Form group that should take ownership of this form submission")
    def __init__(self, queryset, *args, **kwargs):
        super(ChangeOwnerForm, self).__init__(*args, **kwargs)
        self.fields['new_group'].queryset = queryset


class CloseFormForm(forms.Form):
    summary = forms.CharField(required=True,
                help_text="Summary of the form, for advisors (and emailing to student if you select below).",
                widget=forms.TextInput(attrs={'size': '70'})
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
                elif str(name) in post_data:
                    if ignore_required and post_data[str(name)] == "":
                        cleaned_data = ""
                    else:
                        if isinstance(field, MultipleChoiceField):
                            relevant_data = post_data.getlist(str(name))
                            cleaned_data = field.clean(relevant_data)
                        else:
                            cleaned_data = field.clean(post_data[str(name)])
                elif str(name) in files_data:
                    cleaned_data = field.clean(files_data[str(name)])
                else:
                    if ignore_required:
                        cleaned_data = ""
                    else:
                        cleaned_data = field.clean("")
                self.cleaned_data[str(name)] = cleaned_data
                field.initial = cleaned_data
            except forms.ValidationError, e:
                #self.errors[name] = ", ".join(e.messages)
                self.errors[name] = forms.util.ErrorList(e.messages)
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
