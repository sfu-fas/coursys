from datetime import datetime
from django.contrib import messages
from django import forms
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from courselib.auth import NotFoundResponse, ForbiddenResponse, requires_role

from django.db import models
from django.forms import ModelForm
from django.forms.models import modelformset_factory
from django.forms.models import BaseModelFormSet
from django.shortcuts import render_to_response
from django.template import RequestContext

# FormGroup management views
from onlineforms.fieldtypes import *
from onlineforms.forms import FormForm, SheetForm, FieldForm, DynamicForm, GroupForm, EditSheetForm
from onlineforms.models import Form, Sheet, Field, FIELD_TYPE_MODELS, neaten_field_positions, FormGroup
from onlineforms.utils import reorder_sheet_fields

from log.models import LogEntry

def manage_groups(request):
    # for now only display groups the user has created...
    user = request.user.username
    groups = FormGroup.objects.filter(members__userid__startswith=user)
    context = {'groups': groups}
    return render(request, 'onlineforms/manage_groups.html', context)


def new_group(request):
    print "in new group"
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            print "form is valid"
            # unit, name, members
            # FormGroup.objects.create(unit=form.cleaned_data['unit'], name=form.cleaned_data['name'], members=form.cleaned_data['members'])
            form.save()
            print "form created"
            return HttpResponseRedirect(reverse('onlineforms.views.manage_groups'))
    else:
        print "in else"
        form = GroupForm()
    context = {'form': form}
    return render(request, 'onlineforms/new_group.html', context)


def manage_group(request, formgroup_slug):
    # print "in manage group"
    # editting existing form...
    pass


def add_group_member(request, formgroup_slug):
    pass


def remove_group_member(request, formgroup_slug, userid):
    pass

# Form admin views

def list_all(request):
    form = FormForm()
    forms = Form.objects.all()
    context = {'form': form, 'forms': forms}
    return render_to_response('onlineforms/forms.html', context, context_instance=RequestContext(request))


def new_form(request):
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'add':
        form = FormForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('forms')
    else:
        form = FormForm()
    return render_to_response('onlineforms/new_form.html',
            {'form': form},
        context_instance=RequestContext(request))


def view_form(request, form_slug):
    form = get_object_or_404(Form, slug=form_slug)
    sheets = Sheet.objects.filter(form=form, active=True).order_by('order')

    context = {'form': form, 'sheets': sheets}
    return render(request, "onlineforms/view_form.html", context)


def preview_form(request, form_slug):
    owner_form = get_object_or_404(Form, slug=form_slug)
    form_sheets = Sheet.objects.filter(form=owner_form, active=True).order_by('order')

    # need to divide up fields based on sheets (DIVI)
    forms = []
    for sheet in form_sheets:
        form = DynamicForm(sheet.title)
        fieldargs = {}
        fields = Field.objects.filter(sheet=sheet, active=True).order_by('order')
        for field in fields:
            display_field = FIELD_TYPE_MODELS[field.fieldtype](field.config)
            fieldargs[field.id] = display_field.make_entry_field()
        form.setFields(fieldargs)
        forms.append(form)

    context = {'forms': forms, 'owner_form': owner_form}
    return render(request, "onlineforms/preview_form.html", context)


def edit_form(request, form_slug):
    owner_form = get_object_or_404(Form, slug=form_slug)

    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'edit':
        form = FormForm(request.POST, instance=owner_form)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('onlineforms.views.view_form', kwargs={'form_slug': owner_form.slug}))
    else:
        form = FormForm(instance=owner_form)

    context = {'form': form, 'owner_form': owner_form}
    return render(request, 'onlineforms/edit_form.html', context)


def new_sheet(request, form_slug):
    owner_form = get_object_or_404(Form, slug=form_slug)
    form = SheetForm(request.POST or None)
    if form.is_valid():
        Sheet.objects.create(title=form.cleaned_data['title'], form=owner_form)
        messages.success(request, 'Successfully created the new sheet \'%s\'' % form.cleaned_data['title'])

    context = {'form': form, 'owner_form': owner_form}
    return render(request, "onlineforms/new_sheet.html", context)


def edit_sheet(request, form_slug, sheet_slug):
    # http://127.0.0.1:8000/forms/comp-test-form-2/edit/initial-sheet/
    owner_form = get_object_or_404(Form, slug=form_slug)
    owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
    fields = Field.objects.filter(sheet=owner_sheet, active=True).order_by('order')

    # Non Ajax way to reorder activity, please also see reorder_activity view function for ajax way to reorder
    order = None
    field_slug = None
    if request.GET.has_key('order'):
        order = request.GET['order']
    if request.GET.has_key('field_slug'):
        field_slug = request.GET['field_slug']
    if order and field_slug:
        reorder_sheet_fields(fields, field_slug, order)
        return HttpResponseRedirect(
            reverse('onlineforms.views.edit_sheet', kwargs={'form_slug': form_slug, 'sheet_slug': sheet_slug}))

        # check if they are deleting a field from the sheet
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
        field_id = request.POST['field_id']
        fields = Field.objects.filter(id=field_id, sheet=owner_sheet)
        # TODO handle the condition where we cant find the field
        if fields:
            field = fields[0]
            field.active = False
            field.save()
            messages.success(request, 'Removed the field %s.' % (field.label))
        return HttpResponseRedirect(
            reverse(edit_sheet, kwargs={'form_slug': owner_form.slug, 'sheet_slug': owner_sheet.slug}))

    # construct a form from this sheets fields
    form = DynamicForm(owner_sheet.title)
    form.fromFields(fields)

    # a list of dictionaries containing the field model object(for editing) and the field form object(for display)
    modelFormFields = []
    for (counter, field) in enumerate(form):
        modelFormFields.append({'modelField': fields[counter], 'formField': field})

    context = {'owner_form': owner_form, 'owner_sheet': owner_sheet, 'form': form, 'fields': modelFormFields}
    return render(request, "onlineforms/edit_sheet.html", context)


def reorder_field(request, form_slug, sheet_slug):
    """
    Ajax way to reorder activity.
    This ajax view function is called in the edit_sheet page.
    """
    form = get_object_or_404(Form, slug=form_slug)
    sheet = get_object_or_404(Sheet, slug=sheet_slug)
    if request.method == 'POST':
        neaten_field_positions(sheet)
        # find the fields in question
        id_up = request.POST.get('id_up')
        id_down = request.POST.get('id_down')
        if id_up == None or id_down == None:
            return ForbiddenResponse(request)
            # swap the order of the two fields
        field_up = get_object_or_404(Field, id=id_up, sheet=sheet)
        field_down = get_object_or_404(Field, id=id_down, sheet=sheet)

        temp = field_up.order
        field_up.order = field_down.order
        field_down.order = temp
        field_up.save()
        field_down.save()

        return HttpResponse("Order updated!")
    return ForbiddenResponse(request)

def edit_sheet_info(request, form_slug, sheet_slug):
    owner_form = get_object_or_404(Form, slug=form_slug)
    owner_sheet = get_object_or_404(Sheet, slug=sheet_slug)

    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'edit':
        form = EditSheetForm(request.POST, instance=owner_sheet)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('onlineforms.views.edit_sheet', kwargs={'form_slug': owner_form.slug, 'sheet_slug': owner_sheet.slug}))
    else:
        form = EditSheetForm(instance=owner_sheet)

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet}
    return render(request, 'onlineforms/edit_sheet_info.html', context)


def new_field(request, form_slug, sheet_slug):
    #Test url: http://localhost:8000/forms/comp-test-form-2/edit/initial-sheet/new
    #TODO: Add proper security checks.

    owner_form = get_object_or_404(Form, slug=form_slug)
    owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)

    section = 'select'
    type = None

    need_choices = False

    if request.method == 'POST':
        if 'next_section' in request.POST:
            section = request.POST['next_section']
        if section == 'config':
            custom_config = {}
            if 'type' in request.POST:
                type = request.POST['type']
                type_model = FIELD_TYPE_MODELS[type]
                field = type_model()
            else:
                type = request.POST['type_name']
                type_model = FIELD_TYPE_MODELS[type]
                custom_config = _clean_config(request.POST)
                field = type_model(config=custom_config)

            form = field.make_config_form()
            need_choices = field.require_choices()

            if form.is_valid():
                Field.objects.create(label=form.cleaned_data['label'],
                    sheet=owner_sheet,
                    fieldtype=type,
                    config=custom_config,
                    active=True,
                    original=None, )
                messages.success(request, 'Successfully created the new field \'%s\'' % form.cleaned_data['label'])
                section = 'select'
                need_choices = False

    if section == 'select':
        form = FieldForm()
        section = 'config'

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet, 'section': section, 'type_name': type
        , 'choices': need_choices}
    return render(request, 'onlineforms/new_field.html', context)


def _clean_config(config):
    irrelevant_fields = ['csrfmiddlewaretoken', 'next_section', 'type_name']
    clean_config = {key: value for (key, value) in config.iteritems() if key not in irrelevant_fields}
    clean_config['required'] = 'required' in clean_config

    return clean_config


def edit_field(request, form_slug, sheet_slug, field_slug):
    #Test url: http://localhost:8000/forms/comp-test-form-2/edit/initial-sheet/*label of a field*

    owner_form = get_object_or_404(Form, slug=form_slug)
    owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
    field = get_object_or_404(Field, sheet=owner_sheet, slug=field_slug)

    if request.POST:
        clean_config = _clean_config(request.POST)
        form = FIELD_TYPE_MODELS[field.fieldtype](config=clean_config).make_config_form()

        if field.config == clean_config:
            messages.info(request, "Nothing modified")

        elif form.is_valid():
            new_field = Field.objects.create(label=form.cleaned_data['label'],
                sheet=owner_sheet,
                fieldtype=field.fieldtype,
                config=clean_config,
                active=True,
                order=field.order,
                original=field.original)
            messages.success(request, 'Successfully updated the field \'%s\'' % form.cleaned_data['label'])

            return HttpResponseRedirect(
                reverse('onlineforms.views.edit_field', args=(form_slug, sheet_slug, new_field.slug)))

    else:
        form = FIELD_TYPE_MODELS[field.fieldtype](config=field.config).make_config_form()

    context = {'form': form, 'slug_form': form_slug, 'slug_sheet': sheet_slug, 'slug_field': field_slug}

    return render(request, 'onlineforms/edit_field.html', context)

# Form-filling views

def view_submission(request, form_slug, formsubmit_slug):
    pass


def sheet_submission(request, form_slug, sheet_slug):
    pass
