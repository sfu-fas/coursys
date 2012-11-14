from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django import forms
from django.forms.fields import FileField
from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core.urlresolvers import reverse
from courselib.auth import NotFoundResponse, ForbiddenResponse, requires_role, requires_form_admin_by_slug,\
    requires_formgroup

from django.db import models
from django.forms import ModelForm
from django.forms.models import modelformset_factory
from django.forms.models import BaseModelFormSet
from django.template import RequestContext
from django.core.exceptions import ObjectDoesNotExist

# FormGroup management views
from onlineforms.fieldtypes import *
from onlineforms.forms import FormForm, SheetForm, FieldForm, DynamicForm, GroupForm, EditSheetForm, NonSFUFormFillerForm, AdminAssignForm, EditGroupForm, EmployeeSearchForm
from onlineforms.fieldtypes.other import FileCustomField
from onlineforms.models import Form, Sheet, Field, FIELD_TYPE_MODELS, neaten_field_positions, FormGroup, FieldSubmissionFile
from onlineforms.models import FormSubmission, SheetSubmission, FieldSubmission
from onlineforms.models import NonSFUFormFiller, FormFiller
from onlineforms.utils import reorder_sheet_fields

from coredata.models import Person, Role
from log.models import LogEntry
from datetime import datetime

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
        form = EditGroupForm(instance=group)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('onlineforms.views.manage_groups'))
    else:
        form = EditGroupForm(instance=group)
    #form.fields['unit'].choices = unit_choices
    grouplist = FormGroup.objects.filter(slug__exact=formgroup_slug)


    # below is for finding person thru coredata/personfield and adding to group
    """
    if request.method == 'POST': 
        search_form = EmployeeSearchForm(request.POST)
        if not form.is_valid():
            simsearch = None
            if 'search' in form.data and form.data['search'].strip().isdigit():
                simseach = form.data['search'].strip()
            context = {'form': form, 'group': group, 'grouplist': grouplist, 'search': search_form, 'simsearch': simsearch}
    """
    search_form = EmployeeSearchForm()


    context = {'form': form, 'group': group, 'grouplist': grouplist, 'search': search_form }
    return render(request, 'onlineforms/manage_group.html', context)


@requires_role('ADMN')
def add_group_member(request, formgroup_slug):
    group = FormGroup.objects.get(slug=formgroup_slug)
    if group.unit not in request.units:
        return ForbiddenResponse(request)

    print "in add_group_member"
    if request.method == 'POST':
        if 'action' in request.POST:
            if request.POST['action'] == 'add':
                print "Request method stuff"
                post_data = request.POST.values()
                member_id = int(post_data[len(post_data)-1])
                member = Person.objects.get(emplid=member_id)
                group.members.add(member)
                return HttpResponseRedirect(reverse('onlineforms.views.manage_group', kwargs={'formgroup_slug': formgroup_slug}))

@requires_role('ADMN')
def remove_group_member(request, formgroup_slug, userid):
    group = FormGroup.objects.get(slug=formgroup_slug)
    member = Person.objects.get(emplid=userid)

    if group.unit not in request.units:
        return ForbiddenResponse(request)

    # remove m2m relationship
    if request.method == 'POST':
        if 'action' in request.POST:
            if request.POST['action'] == 'remove':
                group.members.remove(member)
                return HttpResponseRedirect(reverse('onlineforms.views.manage_group', kwargs={'formgroup_slug': formgroup_slug}))



# Form admin views
@requires_formgroup()
def admin_list_all(request):
    admin = get_object_or_404(Person, userid=request.user.username)
    form_groups = FormGroup.objects.filter(members=admin)
    if form_groups:
        pend_submissions = FormSubmission.objects.filter(owner__in=form_groups, status='PEND')
        wait_submissions = FormSubmission.objects.filter(owner__in=form_groups, status='WAIT')
        for wait_sub in wait_submissions:
            last_sheet_assigned = SheetSubmission.objects.filter(form_submission=wait_sub).latest('given_at')
            wait_sub.assigned_to = last_sheet_assigned
        done_submissions = FormSubmission.objects.filter(owner__in=form_groups, status='DONE')

    context = {'pend_submissions': pend_submissions, 'wait_submissions': wait_submissions, 'done_submissions': done_submissions}
    return render(request, "onlineforms/admin/admin_forms.html", context)

@requires_formgroup()
def admin_assign(request, formsubmit_slug):
    form_submission = get_object_or_404(FormSubmission, slug=formsubmit_slug)
    form = AdminAssignForm(data=request.POST or None, label='sheet', 
        query_set=Sheet.objects.filter(form=form_submission.form, active=True))
    if form.is_valid():
        # make new sheet submission for next sheet choosen
        assignee = form.cleaned_data['assignee']
        SheetSubmission.objects.create(form_submission=form_submission,
            sheet=form.cleaned_data['sheet'],
            filler=userToFormFiller(assignee))

        # change form submission status back to wait status
        form_submission.status = 'WAIT'
        form_submission.save()
        return HttpResponseRedirect(reverse('onlineforms.views.admin_list_all'))

    context = {'form': form, 'form_submission': form_submission}
    return render(request, "onlineforms/admin/admin_assign.html", context)
    
@requires_formgroup()
def admin_assign_any(request):
    form = AdminAssignForm(data=request.POST or None, label='form', 
        query_set=Form.objects.filter(active=True))
    if form.is_valid():
        assignee = form.cleaned_data['assignee']
        # create new form submission with a blank sheet submission 
        form = form.cleaned_data['form']
        user = userToFormFiller(assignee)
        
        # selector for assigning if in multiple form groups?
        """FormSubmission.objects.create(form=form, initiator=user, 
        SheetSubmission.objects.create(form_submission=form_submission,
            sheet=Sheet.objects.filter(form=form, is_initial=True, active=True)
            filler=user)"""

        return HttpResponseRedirect(reverse('onlineforms.views.admin_list_all'))

    context = {'form': form}
    return render(request, "onlineforms/admin/admin_assign_any.html", context)

@requires_formgroup()
def admin_done(request, formsubmit_slug):
    form_submission = get_object_or_404(FormSubmission, slug=formsubmit_slug)
    form_submission.status = 'DONE'
    form_submission.save()
    return HttpResponseRedirect(reverse('onlineforms.views.admin_list_all'))

def userToFormFiller(user):
    try:
        form_filler = FormFiller.objects.get(sfuFormFiller=user)
    except ObjectDoesNotExist:
        form_filler = FormFiller.objects.create(sfuFormFiller=user)
    return form_filler

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
    return render(request, 'onlineforms/new_form.html', {'form': form})


@requires_form_admin_by_slug()
def view_form(request, form_slug):
    form = get_object_or_404(Form, slug=form_slug)
    sheets = Sheet.objects.filter(form=form, active=True).order_by('order')
     # just for testing active and nonactive sheets
    nonactive_sheets = Sheet.objects.filter(form=form, active=False).order_by('order') 
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
        sheet_id = request.POST['sheet_id']
        sheets = Sheet.objects.filter(id=sheet_id, form=form)
        # TODO handle the condition where we cant find the field
        if sheets :       
                sheet = sheets[0]
                sheet.delete()
                messages.success(request, 'Removed the sheet %s.' % (sheet.title))
           
        return HttpResponseRedirect(
            reverse(view_form, kwargs={'form_slug':form.slug }))

    
    context = {'form': form, 'sheets': sheets, 'nonactive_sheets': nonactive_sheets}
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
            f.save()
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
    owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
    #owner_field = get_object_or_404(Field, slug=field_slug)

    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'edit':
        form = EditSheetForm(request.POST, instance=owner_sheet)
        if form.is_valid():
            new_sheet = owner_sheet.safe_save()
            return HttpResponseRedirect(reverse('onlineforms.views.edit_sheet',
                kwargs={'form_slug': owner_form.slug, 'sheet_slug': new_sheet.slug}))
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
    configurable = False

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
            need_choices = field.choices

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
            new_sheet = owner_sheet.safe_save()
            # newfield = field.safe_save()
            new_field = Field.objects.create(label=form.cleaned_data['label'],
                #sheet=owner_sheet,
                sheet=new_sheet,
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
    sheet_submissions = None
    if(request.user.is_authenticated()):
        loggedin_user = get_object_or_404(Person, userid=request.user.username)
        forms = Form.objects.filter(active=True).exclude(initiators='NON')
        sheet_submissions = SheetSubmission.objects.filter(filler=userToFormFiller(loggedin_user)).exclude(status='DONE')
        # get all the form groups the logged in user is a part of
        form_groups = FormGroup.objects.filter(members=loggedin_user)
    else:
        forms = Form.objects.filter(active=True, initiators='ANY')

    dept_admin = Role.objects.filter(role='ADMN', person__userid=request.user.username).count() > 0

    context = {'forms': forms, 'sheet_submissions': sheet_submissions, 'form_groups': form_groups, 'dept_admin': dept_admin}
    return render(request, 'onlineforms/submissions/forms.html', context)


@requires_formgroup()
def view_submission(request, formsubmit_slug):
    print formsubmit_slug
    form_submission = get_object_or_404(FormSubmission, slug=formsubmit_slug)

    sheet_submissions = SheetSubmission.objects.filter(form_submission=form_submission)
    sheet_sub_html = {}
    for sheet_sub in sheet_submissions:
        # get html from feild submissions
        field_submissions = FieldSubmission.objects.filter(sheet_submission=sheet_sub)
        html = ''
        for field_sub in field_submissions:
            display_field = FIELD_TYPE_MODELS[field_sub.field.fieldtype](field_sub.field.config)
            html += display_field.to_html(field_sub)
        sheet_sub_html[sheet_sub.sheet.title] = html

    context = {'sheet_submissions': sheet_sub_html}
    return render(request, 'onlineforms/admin/view_partial_form.html', context)

def sheet_submission(request, form_slug, formsubmit_slug=None, sheet_slug=None, sheetsubmit_slug=None):
    owner_form = get_object_or_404(Form, slug=form_slug)
    # if no one can fill out this form, stop right now
    if owner_form.initiators == "NON":
        context = {'owner_form': owner_form, 'error_msg': "No one can fill out this form."}
        return render(request, 'onlineforms/submissions/sheet_submission.html', context)

    #get the sheet
    if sheet_slug:
        sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
    else:
        if not(owner_form.initial_sheet):
            raise Http404('No sheet found for this form.')
        sheet = owner_form.initial_sheet

    # get their info if they are logged in
    if(request.user.is_authenticated()):
        loggedin_user = get_object_or_404(Person, userid=request.user.username)
        logentry_userid = loggedin_user.userid
        nonSFUFormFillerForm = None
    else:
        loggedin_user = None
        logentry_userid = ""
        # make a form for non sfu people
        nonSFUFormFillerForm = NonSFUFormFillerForm()

    # a field -> field submission lookup
    field_submission_dict = {}
    # get the submission objects(if they exist) and create the form
    if formsubmit_slug and sheetsubmit_slug:
        form_submission = get_object_or_404(FormSubmission, form=owner_form, slug=formsubmit_slug)
        sheet_submission = get_object_or_404(SheetSubmission, sheet=sheet, form_submission=form_submission, slug=sheetsubmit_slug)
        
        # check if this sheet has already been filled
        if sheet_submission.status == "DONE":
            # or maybe show in display only mode
            return NotFoundResponse(request)
        # check that they can access this sheet
        formFillerPerson = sheet_submission.filler.sfuFormFiller
        if not(formFillerPerson) or loggedin_user != formFillerPerson:
            return ForbiddenResponse(request)

        form = DynamicForm(sheet.title)
        form.fromFields(sheet.fields, sheet_submission.field_submissions)

        # populate the field -> fieldSubmission lookup
        for field_submission in sheet_submission.field_submissions:
            field_submission_dict[field_submission.field] = field_submission
    else:
        form = DynamicForm(sheet.title)
        form.fromFields(sheet.fields)
        form_submission = None
        sheet_submission = None

    if request.method == 'POST' and 'submit-mode' in request.POST:
        submit_modes = ["Save", "Submit"]
        if request.POST["submit-mode"] in submit_modes:
            # get the info from post
            if request.POST["submit-mode"] == "Save":
                form.fromPostData(request.POST, ignore_required=True)
            elif request.POST["submit-mode"] == "Submit":
                form.fromPostData(request.POST)

            if form.is_valid():
                # sheet is valid, lets get a form filler
                formFiller = None
                if 'add-nonsfu' in request.POST and owner_form.initiators == "ANY":
                    nonSFUFormFillerForm = NonSFUFormFillerForm(request.POST)
                    if nonSFUFormFillerForm.is_valid():
                        nonSFUFormFiller = nonSFUFormFillerForm.save()
                        #LOG EVENT#
                        l = LogEntry(userid=logentry_userid,
                            description=("Non SFU Form Filler created with email %s to submit form %s") % (nonSFUFormFiller.email_address, owner_form.title),
                            related_object=nonSFUFormFiller)
                        l.save()
                        formFiller = FormFiller(nonSFUFormFiller=nonSFUFormFiller)
                        formFiller.save()
                elif loggedin_user:
                    formFiller = userToFormFiller(loggedin_user)
                else:
                    # they didn't provide nonsfu info and they are not logged in
                    context = {'owner_form': owner_form,
                               'error_msg': "You must have a SFU account and be logged in to fill out this form."}
                    return render(request, 'onlineforms/submissions/sheet_submission.html', context)

                if formFiller:
                    # we have a form filler, the data is valid, create the formsubmission and sheetsubmission objects if necessary
                    if not(form_submission):
                        # create the form submission
                        form_submission = FormSubmission(form=owner_form, initiator=formFiller, owner=owner_form.owner)
                        form_submission.save()
                        #LOG EVENT#
                        l = LogEntry(userid=logentry_userid,
                            description=("Form submission created for form %s by %s") % (owner_form.title, formFiller.email()),
                            related_object=form_submission)
                        l.save()
                    if not(sheet_submission):
                        # create the sheet submission
                        sheet_submission = SheetSubmission(sheet=sheet, form_submission=form_submission, filler=formFiller)
                        sheet_submission.save()
                        #LOG EVENT#
                        l = LogEntry(userid=logentry_userid,
                            description=("Sheet submission created for sheet %s of form %s by %s") % (sheet.title, owner_form.title, formFiller.email()),
                            related_object=sheet_submission)
                        l.save()

                    # save the data from the fields
                    for name, field in form.fields.items():
                        # a field can be skipped if we are saving and it is not in the cleaned data
                        if not(request.POST["submit-mode"] == "Save") or str(name) in form.cleaned_data:
                            cleaned_data = form.display_fields[field].serialize_field(form.cleaned_data[str(name)])
                            # if we already have a field submission, edit it. Otherwise create a new one
                            if sheet.fields[name] in field_submission_dict:
                                fieldSubmission = field_submission_dict[sheet.fields[name]]
                                fieldSubmission.data = cleaned_data
                            else:
                                fieldSubmission = FieldSubmission(field=sheet.fields[name], sheet_submission=sheet_submission, data=cleaned_data)
                            fieldSubmission.save()
                            # save files
                            if isinstance(field, FileField):
                                if str(name) in request.FILES:
                                    new_file = request.FILES[str(name)]
                                    new_file_submission = FieldSubmissionFile(field_submission=fieldSubmission, file_attachment=new_file, file_mediatype=new_file.content_type)
                                    new_file_submission.save()
                            #LOG EVENT#
                            l = LogEntry(userid=logentry_userid,
                                description=("Field submission created for field %s of sheet %s of form %s by %s") % (sheet.fields[name].label, sheet.title, owner_form.title, formFiller.email()),
                                related_object=fieldSubmission)
                            l.save()

                    # cleanup for each submit-mode
                    if request.POST["submit-mode"] == "Save":
                        # refill the form with the new data
                        form.fromFields(sheet.fields, sheet_submission.get_field_submissions(refetch=True))
                        # don't redirect, show the form with errors(if they exist) but notify them that info was saved
                        messages.success(request, 'All fields without errors were saved.')
                    elif request.POST["submit-mode"] == "Submit":
                        # all the fields have been submitted, this sheet is done
                        sheet_submission.status = 'DONE'
                        sheet_submission.save()
                        l = LogEntry(userid=logentry_userid,
                            description=("Sheet submission %s completed by %s") % (sheet_submission.slug, formFiller.email()),
                            related_object=sheet_submission)
                        l.save()

                        messages.success(request, 'You have succesfully completed sheet %s of form %s.' % (sheet.title, owner_form.title))
                        return HttpResponseRedirect(reverse(submissions_list_all_forms))
            else:
                messages.error(request, "The form could not be submitted because of errors in the supplied data, please correct them and try again.")
        else:
            messages.error(request, 'Invalid post data.')
 
    context = { 'owner_form': owner_form,
                'sheet': sheet, 
                'form': form,
                'nonSFUFormFillerForm': nonSFUFormFillerForm}
    return render(request, 'onlineforms/submissions/sheet_submission.html', context)
