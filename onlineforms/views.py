from datetime import datetime
from django.contrib import messages
from django import forms
from django.shortcuts import render, get_object_or_404, get_list_or_404
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
from onlineforms.forms import FormForm, SheetForm, FieldForm, DynamicForm, GroupForm, EditSheetForm, NonSFUFormFillerForm
from onlineforms.models import Form, Sheet, Field, FIELD_TYPE_MODELS, neaten_field_positions, FormGroup
from onlineforms.models import FormSubmission, SheetSubmission, FieldSubmission
from onlineforms.models import NonSFUFormFiller, FormFiller
from onlineforms.utils import reorder_sheet_fields

from coredata.models import Person, Role
from log.models import LogEntry

def manage_groups(request):
    # for now only display groups the user has created...


    if request.method == 'POST':
        if 'action' in request.POST:
            if request.POST['action'] == 'delete':
                print "if request.post['action'] == delete "
                if 'group_id' in request.POST: 
                    selected_group = FormGroup.objects.filter(pk=request.POST['group_id'])
                    selected_group.delete()
 
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
    """    print "in manage group"
    # editting existing form...
    group = FormGroup.objects.get(slug=formgroup_slug)
    print group
    form = GroupForm(instance=group)
    context = {'group': group}
    """
    return render(request, 'onlineforms/manage_group.html', context)


def add_group_member(request, formgroup_slug):
    pass


def remove_group_member(request, formgroup_slug, userid):
    pass

# Form admin views

def list_all(request):
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
        form_id = request.POST['form_id']
        forms = Form.objects.filter(id=form_id)
        if forms:
            form = forms[0]
            form.delete()
            messages.success(request, 'Removed the Form ')
        return HttpResponseRedirect(reverse(list_all))
    else:
        form = FormForm()
        forms = Form.objects.all()
        context = {'form': form, 'forms': forms}
    return render_to_response('onlineforms/manage_forms.html', context, context_instance=RequestContext(request))


def new_form(request):
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'add':
        form = FormForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('onlineforms.views.list_all'))
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
   # owner_sheet = owner_form.sheets
    #ownersheets = owner_form.sheets

    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'edit':
        form = FormForm(request.POST, instance=owner_form)
        #osheet = form.sheets
        if form.is_valid():
            # define the method to save instance of sheets-- cant attach sheets to form since its an object
#            owner_sheet = owner_form.sheets

 #           owner_form.pk = None
           # owner_form = form.save(duplicate_and_save=True)
           # owner_form = form.save()
            owner_form = form.save()

           # for sheet in owner_form.sheets.all():
            #    owner_form.sheets.add(owner_sheet)

            owner_form.save()    
           # owner_form.sheets = owner_sheet
            return HttpResponseRedirect(reverse('onlineforms.views.view_form', kwargs={'form_slug': owner_form.slug}))
    else:
        form = FormForm(instance=owner_form)

    context = {'form': form, 'owner_form': owner_form}
    return render(request, 'onlineforms/edit_form.html', context)


def new_sheet(request, form_slug):
    owner_form = get_object_or_404(Form, slug=form_slug)
    form = SheetForm(request.POST or None)
    if form.is_valid():
        Sheet.objects.create(title=form.cleaned_data['title'], form=owner_form, can_view=form.cleaned_data['can_view'])
        messages.success(request, 'Successfully created the new sheet \'%s\'' % form.cleaned_data['title'])
        return HttpResponseRedirect(
            reverse('onlineforms.views.view_form', args=(form_slug,)))

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
            return HttpResponseRedirect(reverse('onlineforms.views.edit_sheet',
                kwargs={'form_slug': owner_form.slug, 'sheet_slug': owner_sheet.slug}))
    else:
        form = EditSheetForm(instance=owner_sheet)

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet}
    return render(request, 'onlineforms/edit_sheet_info.html', context)


def new_field(request, form_slug, sheet_slug):

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
            need_choices = field.choices

            if form.is_valid():
                Field.objects.create(label=form.cleaned_data['label'],
                    sheet=owner_sheet,
                    fieldtype=type,
                    config=custom_config,
                    active=True,
                    original=None, )
                messages.success(request, 'Successfully created the new field \'%s\'' % form.cleaned_data['label'])

                return HttpResponseRedirect(
                    reverse('onlineforms.views.edit_sheet', args=(form_slug, sheet_slug)))
                
    if section == 'select':
        form = FieldForm()
        section = 'config'

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet, 'section': section, 'type_name': type
        , 'choices': need_choices}
    return render(request, 'onlineforms/new_field.html', context)


def _clean_config(config):
    irrelevant_fields = ['csrfmiddlewaretoken', 'next_section', 'type_name']
    clean_config = dict((key, value) for (key, value) in config.iteritems() if key not in irrelevant_fields)
    clean_config['required'] = 'required' in clean_config

    return clean_config


def edit_field(request, form_slug, sheet_slug, field_slug):

    owner_form = get_object_or_404(Form, slug=form_slug)
    owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
    field = get_object_or_404(Field, sheet=owner_sheet, slug=field_slug)

    type = FIELD_TYPE_MODELS[field.fieldtype]
    need_choices = type().choices

    if request.POST:
        clean_config = _clean_config(request.POST)
        form = type(config=clean_config).make_config_form()

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
                reverse('onlineforms.views.edit_sheet', args=(form_slug, sheet_slug)))

    else:
        form = FIELD_TYPE_MODELS[field.fieldtype](config=field.config).make_config_form()

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet, 'field': field,
               'choices': need_choices}

    return render(request, 'onlineforms/edit_field.html', context)

# Form-filling views

def submissions_list_all_forms(request):
    roles = []
    if(request.user.is_authenticated()):
        forms = Form.objects.filter(active=True).exclude(initiators='NON')
        userid = request.user.username
        roles = Role.all_roles(userid)
    else:
        forms = Form.objects.filter(active=True, initiators='ANY')
    
    context = {'forms': forms, 'roles': roles}
    return render_to_response('onlineforms/submissions/forms.html', context, context_instance=RequestContext(request))

def form_initial_submission(request, form_slug):
    owner_form = get_object_or_404(Form, slug=form_slug)
    # if no one can fill out this form, stop right now
    if owner_form.initiators == "NON":
        context = {'owner_form': owner_form, 'error_msg': "No one can fill out this form."}
        return render_to_response('onlineforms/submissions/initial_sheet.html', context, context_instance=RequestContext(request))

    sheet = owner_form.initial_sheet

    if(request.user.is_authenticated()):
        loggedin_user = get_object_or_404(Person, userid=request.user.username)
    else:
        loggedin_user = None

    if request.method == 'POST':
        # validate the sheet
        form = DynamicForm(sheet.title)
        form.fromFields(sheet.fields)
        form.validate(request.POST)
        # TODO: actually check that this info was valid

        # sheet is valid, lets get a form filler
        if 'add-nonsfu' in request.POST and owner_form.initiators == "ANY":
            nonSFUFormFillerForm = NonSFUFormFillerForm(request.POST)
            if nonSFUFormFillerForm.is_valid():
                nonSFUFormFiller = nonSFUFormFillerForm.save()
                formFiller = FormFiller(nonSFUFormFiller=nonSFUFormFiller)
                formFiller.save()
                # TODO: LOGGING
        elif loggedin_user:
            formFiller = FormFiller(sfuFormFiller=loggedin_user)
            formFiller.save()
            # TODO: LOGGING
        else:
            # they didn't provide nonsfu info and they are not logged in
            context = {'owner_form': owner_form, 'error_msg': "You must have a SFU account and be logged in to fill out this form."}
            return render_to_response('onlineforms/submissions/initial_sheet.html', context, context_instance=RequestContext(request))

        # create the form submission
        formSubmission = FormSubmission(form=owner_form, initiator=formFiller, owner=owner_form.owner)
        formSubmission.save()
        # TODO:logging

        # create the sheet submission
        sheetSubmission = SheetSubmission(sheet=sheet, form_submission=formSubmission, filler=formFiller)
        sheetSubmission.save()
        # TODO:logging

        for name, field in form.fields.items():
            cleaned_data = field.clean(request.POST[str(name)])
            # name is just a number, we can use it as the index
            fieldSubmission = FieldSubmission(field=sheet.fields[name], sheet_submission=sheetSubmission, data=cleaned_data)
            fieldSubmission.save()
            # TODO:logging

        messages.success(request, 'You have succesfully submitted %s.' % (owner_form.title))
        return HttpResponseRedirect(reverse(submissions_list_all_forms))


    # if the user is not logged in and this is an any form, show the no sfu form filler, otherwise reject them
    if not(loggedin_user):
        if owner_form.initiators == "ANY":
            nonSFUFormFillerForm = NonSFUFormFillerForm()
        else:
            context = {'owner_form': owner_form, 'error_msg': "You must have a SFU account and be logged in to fill out this form."}
            return render_to_response('onlineforms/submissions/initial_sheet.html', context, context_instance=RequestContext(request))
    else:
        nonSFUFormFillerForm = None

    form = DynamicForm(sheet.title)
    form.fromFields(sheet.fields)

    context = {'owner_form': owner_form, 'sheet': sheet, 'form': form, 'nonSFUFormFillerForm': nonSFUFormFillerForm}
    return render_to_response('onlineforms/submissions/initial_sheet.html', context, context_instance=RequestContext(request))


def view_submission(request, form_slug, formsubmit_slug):
    pass


def sheet_submission(request, form_slug, sheet_slug):
    pass
