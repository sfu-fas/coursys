from datetime import datetime
from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from courselib.auth import NotFoundResponse, ForbiddenResponse, requires_role

# FormGroup management views
from onlineforms.forms import ConfigFieldForm
from onlineforms.models import Form, Sheet, Field

def manage_groups(request):
    pass


def new_group(request):
    pass


def manage_group(request, formgroup_slug):
    pass


def add_group_member(request, formgroup_slug):
    pass


def remove_group_member(request, formgroup_slug, userid):
    pass

# Form admin views

def list_all(request):
    pass


def new_form(request):
    pass


def view_form(request, form_slug):
    form = DynamicForm()
    
    fields = {}
    fields['a_name'] = forms.CharField(label="Name", max_length=25, help_text="name")
    fields['b_lname'] = forms.CharField(label="Last Name", help_text="lname")
    fields['c_bday'] = forms.DateField(label="Birthday", help_text="birthday")
    form.setFields(fields)
    
    context =  {'form': form}
    return render(request, "onlineforms/view_form.html", context)


def edit_form(request, form_slug):
    pass


def new_sheet(request, form_slug):
    pass


def edit_sheet(request, form_slug, sheet_slug):
    pass


def new_field(request, form_slug, sheet_slug):
    #Test url: http://localhost:8000/forms/comp-test-form-1/edit/initial-sheet/new
    owner_form = get_object_or_404(Form, slug=form_slug) #Maybe only owner_sheet is needed
    owner_sheet = get_object_or_404(Sheet, slug=sheet_slug)
    print owner_sheet

    if request.method == 'POST':
        form = ConfigFieldForm(request.POST)
        if form.is_valid():
            custom_config = {}

            Field.objects.create(label=form.cleaned_data['name'],
                sheet=owner_sheet,
                required=form.cleaned_data['required'],
                fieldtype=form.cleaned_data['type'],
                config=custom_config,
                active=True,
                original=None,
                created_date=datetime.now(),
                last_modified=datetime.now())

            messages.success(request, 'Successfully created the new field \'%s\'' % form.cleaned_data['name'])
        else:
            print "Invalid"

    else:
        form = ConfigFieldForm()

    context = {'form': form, 'slug_form': form_slug, 'slug_sheet': sheet_slug}
    return render(request, 'onlineforms/new_field.html', context)


def edit_field(request, form_slug, sheet_slug, field_slug):
    #Test url: http://localhost:8000/forms/comp-test-form-1/edit/initial-sheet/edit

    context = {}
    return render(request, 'onlineforms/edit_field.html', context)
    pass

# Form-filling views

def view_submission(request, form_slug, formsubmit_slug):
    pass


def sheet_submission(request, form_slug, sheet_slug):
    pass

