from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django import forms
from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from courselib.auth import NotFoundResponse, ForbiddenResponse, requires_role, requires_form_admin_by_slug, \
        requires_formgroup

from django.db import models
from django.forms import ModelForm
from django.forms.models import modelformset_factory
from django.forms.models import BaseModelFormSet
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

@requires_role('ADMN')
def manage_groups(request):
    #if request.method == 'POST':
    #    if 'action' in request.POST:
    #        if request.POST['action'] == 'delete':
    #            print "if request.post['action'] == delete "
    #            if 'group_id' in request.POST:
    #                selected_group = FormGroup.objects.filter(pk=request.POST['group_id'])
    #                selected_group.delete()

    groups = FormGroup.objects.filter(unit__in=request.units)
    context = {'groups': groups}
    return render(request, 'onlineforms/manage_groups.html', context)


@requires_role('ADMN')
def new_group(request):
    unit_choices = [(u.id, unicode(u)) for u in request.units]
    if request.method == 'POST':
        form = GroupForm(request.POST)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            # unit, name, members
            # FormGroup.objects.create(unit=form.cleaned_data['unit'], name=form.cleaned_data['name'], members=form.cleaned_data['members'])
            form.save()
            return HttpResponseRedirect(reverse('onlineforms.views.manage_groups'))
    else:
        form = GroupForm()
        form.fields['unit'].choices = unit_choices
    context = {'form': form}
    return render(request, 'onlineforms/new_group.html', context)


@requires_role('ADMN')
def manage_group(request, formgroup_slug):
    group = FormGroup.objects.get(slug=formgroup_slug)
    if group.unit not in request.units:
        return ForbiddenResponse(request)
    unit_choices = [(u.id, unicode(u)) for u in request.units]

    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('onlineforms.views.manage_groups'))
    else:
        form = GroupForm(instance=group)
        form.fields['unit'].choices = unit_choices

    context = {'form': form, 'group': group}
    return render(request, 'onlineforms/manage_group.html', context)


@requires_role('ADMN')
def add_group_member(request, formgroup_slug):
    group = FormGroup.objects.get(slug=formgroup_slug)
    if group.unit not in request.units:
        return ForbiddenResponse(request)

    pass


@requires_role('ADMN')
def remove_group_member(request, formgroup_slug, userid):
    group = FormGroup.objects.get(slug=formgroup_slug)
    if group.unit not in request.units:
        return ForbiddenResponse(request)

    pass

# Form admin views
@login_required
def admin_list_all(request):
    admin = get_object_or_404(Person, userid=request.user.username)
    form_group = FormGroup.objects.get(members=admin)
    if form_group:
        form_submissions = FormSubmission.objects.filter(owner=form_group, status='WAIT')
    
    context = {'form_submissions': form_submissions}
    return render(request, "onlineforms/admin/admin_forms.html", context)

def admin_assign(request, form_sumbission_slug):
    form_submission = get_object_or_404(FormSubmission, slug=form_sumbission_slug)
    form = AdminAssignForm(request.POST or None, form_submission.owner)
    if form.is_valid():
        # make new sheet submission for next sheet in form
        sheet_order = SheetSubmission.objects.filter(form_submission=form_submission).count()
        sheet = Sheet.objects.get(order=sheet_order, form=form_submission.form)
        SheetSubmission.objects.create(sheet=sheet, form_submission=formSubmission, filler=form.cleaned_data['send_to'])
        return HttpResponseRedirect(reverse('onlineforms.views.admin_list_all'))
    
    context = {'form': form, 'form_submission': form_submission}
    return render(request, "onlineforms/admin/admin_assign.html", context)

@requires_formgroup()
def list_all(request):
    forms = Form.objects.filter(owner__in=request.formgroups, active=True)
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
        form_id = request.POST['form_id']
        forms = forms.filter(id=form_id)
        if forms:
            form = forms[0]
            form.delete()
            messages.success(request, 'Removed the Form ')
        return HttpResponseRedirect(reverse(list_all))
    else:
        form = FormForm()
        context = {'form': form, 'forms': forms}
    return render(request, 'onlineforms/manage_forms.html', context)

@requires_formgroup()
def new_form(request):
    group_choices = [(fg.id, unicode(fg)) for fg in request.formgroups]
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'add':
        form = FormForm(request.POST)
        form.fields['owner'].choices = group_choices
        if form.is_valid():
            f = form.save(commit=False)
            # use FormGroup's unit as the Form's unit
            f.unit = f.owner.unit
            f.save()
            return HttpResponseRedirect(reverse('onlineforms.views.list_all'))
    else:
        form = FormForm()
        form.fields['owner'].choices = group_choices
    return render('onlineforms/new_form.html', {'form': form})

@requires_form_admin_by_slug()
def view_form(request, form_slug):
    form = get_object_or_404(Form, slug=form_slug)
    sheets = Sheet.objects.filter(form=form, active=True).order_by('order')

    context = {'form': form, 'sheets': sheets}
    return render(request, "onlineforms/view_form.html", context)


@requires_form_admin_by_slug()
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


@requires_form_admin_by_slug()
def edit_form(request, form_slug):
    owner_form = get_object_or_404(Form, slug=form_slug)
    group_choices = [(fg.id, unicode(fg)) for fg in request.formgroups]

    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'edit':
        form = FormForm(request.POST, instance=owner_form)
        form.fields['owner'].choices = group_choices
        if form.is_valid():
            f = form.save(commit=False)
            # use FormGroup's unit as the Form's unit
            f.unit = f.owner.unit
            f.save(clone = True)
            return HttpResponseRedirect(reverse('onlineforms.views.view_form', kwargs={'form_slug': owner_form.slug}))
    else:
        form = FormForm(instance=owner_form)
        form.fields['owner'].choices = group_choices

    context = {'form': form, 'owner_form': owner_form}
    return render(request, 'onlineforms/edit_form.html', context)


@requires_form_admin_by_slug()
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


@requires_form_admin_by_slug()
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


@requires_form_admin_by_slug()
def reorder_field(request, form_slug, sheet_slug):
    """
    Ajax way to reorder activity.
    This ajax view function is called in the edit_sheet page.
    """
    form = get_object_or_404(Form, slug=form_slug)
    sheet = get_object_or_404(Sheet, form=form, slug=sheet_slug)
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


@requires_form_admin_by_slug()
def edit_sheet_info(request, form_slug, sheet_slug):
    owner_form = get_object_or_404(Form, slug=form_slug)
    owner_sheet = get_object_or_404(Sheet, slug=sheet_slug)
    #owner_field = get_object_or_404(Field, slug=field_slug)

    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'edit':
        form = EditSheetForm(request.POST, instance=owner_sheet)
        if form.is_valid():
            #Duplicating Sheet through View first then implemnt in Models
            original_form = owner_sheet.form
            original_order = owner_sheet.order
           # original_field = owner_sheet.fields

            #owner_sheet.pk  = None
            #for fields in owner_sheet.fields:
             #       fields = original_field
                    #fields.save()        
            #owner_sheet.field = original_field    

            owner_sheet.form = original_form
            owner_sheet.order = original_order + 1
            
            #owner_sheet.field = original_field    
            owner_sheet = form.save()
            owner_sheet.self_save()
           # owner_sheet.fields.save()
            form.save()
            return HttpResponseRedirect(reverse('onlineforms.views.edit_sheet',
                kwargs={'form_slug': owner_form.slug, 'sheet_slug': owner_sheet.slug}))
    else:
        form = EditSheetForm(instance=owner_sheet)

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet}
    return render(request, 'onlineforms/edit_sheet_info.html', context)


@requires_form_admin_by_slug()
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

            #If the form is not configurable (such as a divider) there's no second form.
            configurable = field.configurable
            if not configurable:
                Field.objects.create(label='',
                    sheet=owner_sheet,
                    fieldtype=type,
                    config=None,
                    active=True,
                    original=None, )
                messages.success(request, 'Successfully created a new divider field')

                return HttpResponseRedirect(
                    reverse('onlineforms.views.edit_sheet', args=(form_slug, sheet_slug)))

            need_choices = field.choices

            #If the form is configurable it must be validated
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


@requires_form_admin_by_slug()
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
        if not type.configurable:
            return HttpResponseRedirect(
                reverse('onlineforms.views.edit_sheet', args=(form_slug, sheet_slug)))
        form = FIELD_TYPE_MODELS[field.fieldtype](config=field.config).make_config_form()

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet, 'field': field,
               'choices': need_choices}

    return render(request, 'onlineforms/edit_field.html', context)

# Form-filling views

def submissions_list_all_forms(request):
    form_groups = None
    if(request.user.is_authenticated()):
        loggedin_user = get_object_or_404(Person, userid=request.user.username)
        forms = Form.objects.filter(active=True).exclude(initiators='NON')
        # get all the form groups the logged in user is a part of
        form_groups = FormGroup.objects.filter(members=loggedin_user)
    else:
        forms = Form.objects.filter(active=True, initiators='ANY')
    
    dept_admin = Role.objects.filter(role='ADMN', person__userid=request.user.username).count() > 0

    context = {'forms': forms, 'form_groups': form_groups, 'dept_admin': dept_admin}
    return render(request, 'onlineforms/submissions/forms.html', context)


def form_initial_submission(request, form_slug):
    owner_form = get_object_or_404(Form, slug=form_slug)
    # if no one can fill out this form, stop right now
    if owner_form.initiators == "NON":
        context = {'owner_form': owner_form, 'error_msg': "No one can fill out this form."}
        return render(request, 'onlineforms/submissions/initial_sheet.html', context)

    sheet = owner_form.initial_sheet

    if(request.user.is_authenticated()):
        loggedin_user = get_object_or_404(Person, userid=request.user.username)
    else:
        loggedin_user = None

    if request.method == 'POST':
        # validate the sheet
        form = DynamicForm(sheet.title)
        form.fromFields(sheet.fields)
        form.fromPostData(request.POST)

        if form.is_valid():
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
                context = {'owner_form': owner_form,
                           'error_msg': "You must have a SFU account and be logged in to fill out this form."}
                return render(request, 'onlineforms/submissions/initial_sheet.html', context)

            # create the form submission
            formSubmission = FormSubmission(form=owner_form, initiator=formFiller, owner=owner_form.owner)
            formSubmission.save()
            # TODO:logging

            # create the sheet submission
            sheetSubmission = SheetSubmission(sheet=sheet, form_submission=formSubmission, filler=formFiller)
            sheetSubmission.save()
            # TODO:logging

            for name, field in form.fields.items():
                cleaned_data = form.display_fields[field].serialize_field(form.cleaned_data[str(name)])
                # name is just a number, we can use it as the index
                fieldSubmission = FieldSubmission(field=sheet.fields[name], sheet_submission=sheetSubmission, data=cleaned_data)
                fieldSubmission.save()
                # TODO:logging

            messages.success(request, 'You have succesfully submitted %s.' % (owner_form.title))
            return HttpResponseRedirect(reverse(submissions_list_all_forms))
    else:      
        form = DynamicForm(sheet.title)
        form.fromFields(sheet.fields)


    # if the user is not logged in and this is an any form, show the no sfu form filler, otherwise reject them
    if not(loggedin_user):
        if owner_form.initiators == "ANY":
            # if the above post failed (i.e. maybe the main forms data was invalid), we may have 
            # non sfu form filler data we want to maintain
            if request.method == 'POST':
                nonSFUFormFillerForm = NonSFUFormFillerForm(request.POST)
            else:
                nonSFUFormFillerForm = NonSFUFormFillerForm()
        else:
            context = {'owner_form': owner_form,
                       'error_msg': "You must have a SFU account and be logged in to fill out this form."}
            return render(request, 'onlineforms/submissions/initial_sheet.html', context)
    else:
        nonSFUFormFillerForm = None

    context = {'owner_form': owner_form, 'sheet': sheet, 'form': form, 'nonSFUFormFillerForm': nonSFUFormFillerForm}
    return render(request, 'onlineforms/submissions/initial_sheet.html', context)


def view_submission(request, form_slug, formsubmit_slug):
    pass


def sheet_submission(request, form_slug, sheet_slug):
    pass
