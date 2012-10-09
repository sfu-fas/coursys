from datetime import datetime
from django.contrib import messages
from django import forms
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from courselib.auth import NotFoundResponse, ForbiddenResponse, requires_role

# FormGroup management views
from onlineforms.forms import FieldForm
from onlineforms.fieldtypes import *
from onlineforms.forms import FieldForm, DynamicForm
from onlineforms.models import Form, Sheet, Field, FIELD_TYPE_MODELS

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

    fields = Field.objects.all();

    # need to divide up fields based on sheets (DIVI)
    fieldargs = {}
    for field in fields:
        display_field = FIELD_TYPE_MODELS[field.fieldtype]()
        fieldargs[field.id] = display_field.make_entry_field()
    form.setFields(fieldargs)

    context = {'form': form}
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
    section = 'setup'

    if request.method == 'POST':
        if 'next_section' in request.POST:
            section = request.POST['next_section']
            #Start with choosing the form in setup, then the forms config after
        if section == 'setup':
            form = FieldForm(request.POST)
            if form.is_valid():
                custom_config = {}# = json.dump(list(all_events), resp, indent=1)

                #Field.objects.create(label=form.cleaned_data['name'],
                #    sheet=owner_sheet,
                #    required=form.cleaned_data['required'],
                #    fieldtype=form.cleaned_data['type'],
                #    config=custom_config,
                #    active=True,
                #    original=None,
                #    created_date=datetime.now(),
                #    last_modified=datetime.now())

                messages.success(request, 'Successfully created the new field \'%s\'' % form.cleaned_data['name'])
            else:
                print "Invalid"
        else:
            #forms config section
            type = request.POST['type']
            type = FIELD_TYPE_MODELS[type]

            field = type()

            #global name 'SmallTextConfigForm' is not defined
            #form = field.make_config_form()

            form = FieldForm()
            print "type: " + str(type)

    else:
        form = FieldForm()

    context = {'form': form, 'slug_form': form_slug, 'slug_sheet': sheet_slug, 'section': section}
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

