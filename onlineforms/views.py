from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import Max
from django.forms.fields import FileField
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.urls import reverse
import django.db.transaction
from django.db.models import Q, Count
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from courselib.auth import ForbiddenResponse, requires_role, requires_form_admin_by_slug,\
    requires_formgroup, login_redirect
from courselib.db import retry_transaction
from courselib.branding import help_email
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from onlineforms.forms import FormForm,NewFormForm, SheetForm, FieldForm, DynamicForm, GroupForm, \
    EditSheetForm, NonSFUFormFillerForm, AdminAssignFormForm, AdminAssignSheetForm, EditGroupForm, EmployeeSearchForm, \
    AdminAssignFormForm_nonsfu, AdminAssignSheetForm_nonsfu, CloseFormForm, ChangeOwnerForm, AdminReturnForm
from onlineforms.models import Form, Sheet, Field, FIELD_TYPE_MODELS, FIELD_TYPES, neaten_field_positions, FormGroup, FormGroupMember, FieldSubmissionFile
from onlineforms.models import FormSubmission, SheetSubmission, FieldSubmission
from onlineforms.models import FormFiller, SheetSubmissionSecretUrl, FormLogEntry, reorder_sheet_fields

from coredata.models import Person, Role, Unit
from coredata.queries import ensure_person_from_userid, SIMSProblem
from log.models import LogEntry
import csv
import json
import os

#######################################################################
# Group Management

@requires_role(['ADMN', 'FORM'])
def manage_groups(request):
    groups = FormGroup.objects.filter(unit__in=Unit.sub_units(request.units))
    context = {'groups': groups}
    return render(request, 'onlineforms/manage_groups.html', context)


@requires_role(['ADMN', 'FORM'])
def new_group(request):
    with django.db.transaction.atomic():
        unit_choices = [(u.id, str(u)) for u in Unit.sub_units(request.units)]
        if request.method == 'POST':
            form = GroupForm(request.POST)
            form.fields['unit'].choices = unit_choices
            if form.is_valid():
                formgroup = form.save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("created form group %s (%i)") % (formgroup, formgroup.id),
                      related_object=formgroup)
                l.save()
                return HttpResponseRedirect(reverse('onlineforms:manage_group', kwargs={'formgroup_slug': formgroup.slug }))
        else:
            form = GroupForm()
            form.fields['unit'].choices = unit_choices

        add_member_form = EmployeeSearchForm()
        context = {'form': form, 'addMemberForm': add_member_form}
        return render(request, 'onlineforms/new_group.html', context)


@requires_role(['ADMN', 'FORM'])
def manage_group(request, formgroup_slug):
    with django.db.transaction.atomic():
        group = get_object_or_404(FormGroup, slug=formgroup_slug, unit__in=Unit.sub_units(request.units))
        groupmembers = FormGroupMember.objects.filter(formgroup=group).order_by('person__last_name')

        # for editting group name
        if request.method == 'POST':
            form = EditGroupForm(request.POST, instance=group)
            if form.is_valid():
                form.save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("edited form group %s (%i)") % (group, group.id),
                      related_object=group)
                l.save()
                return HttpResponseRedirect(reverse('onlineforms:manage_groups'))
        form = EditGroupForm(instance=group)

        # below is for finding person thru coredata/personfield and adding to group
        search_form = EmployeeSearchForm()

        context = {'form': form, 'group': group, 'groupmembers': groupmembers, 'search': search_form }
        return render(request, 'onlineforms/manage_group.html', context)


@requires_role(['ADMN', 'FORM'])
def add_group_member(request, formgroup_slug):
    with django.db.transaction.atomic():
        group = get_object_or_404(FormGroup, slug=formgroup_slug, unit__in=Unit.sub_units(request.units))
        if request.method == 'POST':
            if request.POST['search'] != '':
                search_form = EmployeeSearchForm(request.POST)
                if search_form.is_valid():
                    # search returns Person object
                    person = search_form.cleaned_data['search']
                    email = search_form.cleaned_data['email']
                    # If this FormGroupMember already exists, catch it instead of throwing an exception because of
                    # a violated UNIQUE constraint.
                    if FormGroupMember.objects.filter(person=person, formgroup=group).exists():
                        messages.error(request, "This person is already in this Form Group")
                        return HttpResponseRedirect(
                            reverse('onlineforms:manage_group', kwargs={'formgroup_slug': formgroup_slug}))
                    member = FormGroupMember(person=person, formgroup=group)
                    member.set_email(email)
                    member.save()
                    l = LogEntry(userid=request.user.username,
                         description=("added %s to form group %s (%i)") % (person.userid_or_emplid(), group, group.id),
                         related_object=member)
                    l.save()
                    messages.success(request, "%s added to this Form Group." % person)
                    return HttpResponseRedirect(reverse('onlineforms:manage_group', kwargs={'formgroup_slug': formgroup_slug}))
            else: # if accidentally don't search for anybody
                return HttpResponseRedirect(reverse('onlineforms:manage_group', kwargs={'formgroup_slug': formgroup_slug }))
        
        return HttpResponseRedirect(reverse('onlineforms:manage_group', kwargs={'formgroup_slug': formgroup_slug}))


@requires_role(['ADMN', 'FORM'])
def remove_group_member(request, formgroup_slug, userid):
    with django.db.transaction.atomic():
        group = get_object_or_404(FormGroup, slug=formgroup_slug, unit__in=Unit.sub_units(request.units))
        person = get_object_or_404(Person, emplid=userid)
        member = get_object_or_404(FormGroupMember, person=person, formgroup=group)

        # remove m2m relationship
        if request.method == 'POST':
            member.delete()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Removed %s from form group %s (%i)") % (person.userid_or_emplid(), group, group.id),
                related_object=group)
            l.save()
            return HttpResponseRedirect(reverse('onlineforms:manage_group', kwargs={'formgroup_slug': formgroup_slug}))
        
        groups = FormGroup.objects.filter(unit__in=Unit.sub_units(request.units))
        context = {'groups': groups}
        return render(request, 'onlineforms/manage_groups.html', context)


@requires_role(['ADMN', 'FORM'])
def toggle_group_member(request, formgroup_slug, userid):
    with django.db.transaction.atomic():
        group = get_object_or_404(FormGroup, slug=formgroup_slug, unit__in=Unit.sub_units(request.units))
        person = get_object_or_404(Person, emplid=userid)
        member = get_object_or_404(FormGroupMember, person=person, formgroup=group)

        # remove m2m relationship
        if request.method == 'POST':
            member.set_email(not member.email())
            member.save()
            # LOG EVENT#
            l = LogEntry(userid=request.user.username,
                         description=("Toggled email setting for %s in form group %s (%i)") %
                                     (person.userid_or_emplid(), group, group.id),
                         related_object=group)
            l.save()
            return HttpResponseRedirect(reverse('onlineforms:manage_group', kwargs={'formgroup_slug': formgroup_slug}))

        groups = FormGroup.objects.filter(unit__in=Unit.sub_units(request.units))
        context = {'groups': groups}
        return render(request, 'onlineforms/manage_groups.html', context)



#######################################################################
# Managing submissions & assigning sheets

@requires_formgroup()
def admin_list_all(request):
    admin = get_object_or_404(Person, userid=request.user.username)
    form_groups = FormGroup.objects.filter(members=admin)
    if form_groups:
        pend_submissions = FormSubmission.objects.filter(owner__in=form_groups, status='PEND') \
                .annotate(last_sheet_dt=Max('sheetsubmission__completed_at')) \
                .select_related('initiator__sfuFormFiller', 'initiator__nonSFUFormFiller', 'form')

        #Waiting submissions
        wait_submissions = list(FormSubmission.objects.filter(owner__in=form_groups, status='WAIT') \
                .select_related('initiator__sfuFormFiller', 'initiator__nonSFUFormFiller', 'form'))
        wait_lookup = dict((fs.id, fs) for fs in wait_submissions)
        wait_ss = SheetSubmission.objects.filter(form_submission__in=wait_submissions).order_by('given_at') \
                .select_related('filler__sfuFormFiller', 'filler__nonSFUFormFiller', 'sheet')

        # .assigned_to will be the most recently given_at sheetsub after this
        for ss in wait_ss:
            wait_lookup[ss.form_submission_id].assigned_to = ss
            # We no longer allow returning/assigning the initial sheet.  Let's find out if the sheet that is waiting
            # is the initial sheet, as this would indicate an unsubmitted form.  We should display that in a separate
            # list.  However, the initial sheet can have been assigned manually via the "Assign a form" link.  In those
            # cases, treat it as a normal Waiting form.  The cleanup tasks will also not delete those after 14 days.
            wait_lookup[ss.form_submission_id].is_initial = ss.sheet.is_initial and not ss.assigner()
        #  Let's split up the list between unsubmitted forms and submitted ones.  Most people won't care about the
        # unsubmitted ones.
        unsubmitted_forms = [f for f in wait_submissions if f.is_initial]
        wait_submissions = [f for f in wait_submissions if not f.is_initial]

    # Create a quick summary of pending forms to easily see at the top of the page so one doesn't have to scroll
    # through the whole table to see what needs to be worked on.
    submission_summary = {}
    if pend_submissions:
        for s in pend_submissions:
            if s.form.title in submission_summary:
                submission_summary[s.form.title] += 1
            else:
                submission_summary[s.form.title] = 1
    sub_summary = sorted(submission_summary.items(), key=lambda x: x[1], reverse=True)
    context = {'pend_submissions': pend_submissions, 'wait_submissions': wait_submissions,
               'unsubmitted_forms': unsubmitted_forms, 'sub_summary': sub_summary}
    return render(request, "onlineforms/admin/admin_forms.html", context)


@requires_formgroup()
def admin_assign_nonsfu(request, form_slug, formsubmit_slug):
    return _admin_assign(request, form_slug=form_slug, formsubmit_slug=formsubmit_slug, assign_to_sfu_account=False)

@requires_formgroup()
def admin_assign(request, form_slug, formsubmit_slug, assign_to_sfu_account=True):
    return _admin_assign(request, form_slug=form_slug, formsubmit_slug=formsubmit_slug, assign_to_sfu_account=True)


# Commented out to try to solve sheets getting assigned twice without user interaction
# @retry_transaction()
def _admin_assign(request, form_slug, formsubmit_slug, assign_to_sfu_account=True):
    """
    Give a sheet on this formsubmission to a user
    """
    with django.db.transaction.atomic():
        admin = get_object_or_404(Person, userid=request.user.username)
        form_submission = get_object_or_404(FormSubmission, form__slug=form_slug, slug=formsubmit_slug,
                                            owner__in=request.formgroups)

        # get the next sheet that hasn't been completed (as the default next sheet to assign)
        # ([-1000] ensures there's something for the max() below)
        filled_orders = [-1000] + [val['sheet__order'] for val in
                         form_submission.sheetsubmission_set.filter(status='DONE').values('sheet__order')]
        later_sheets = Sheet.objects \
                       .filter(form=form_submission.form, active=True, order__gt=max(filled_orders)) \
                       .order_by('order')
        default_sheet = later_sheets[0] if later_sheets else None

        sheets = Sheet.objects.filter(form=form_submission.form, active=True, is_initial=False)
        assign_args = {'data': request.POST or None,
                        'query_set': sheets,
                        'initial': {'sheet': default_sheet}}
        form = AdminAssignSheetForm(**assign_args) if assign_to_sfu_account else AdminAssignSheetForm_nonsfu(**assign_args)

        if request.method == 'POST' and form.is_valid():
            if assign_to_sfu_account:
                formFiller = _userToFormFiller(form.cleaned_data['assignee'])
            else:
                nonSFUFormFiller = form.save()  # in this case the form is a model form
                formFiller = FormFiller.objects.create(nonSFUFormFiller=nonSFUFormFiller)

            sheet_submission = SheetSubmission(form_submission=form_submission,
                sheet=form.cleaned_data['sheet'],
                filler=formFiller)
            sheet_submission.set_assigner(admin)
            if 'note' in form.cleaned_data and form.cleaned_data['note']:
                sheet_submission.set_assign_note(form.cleaned_data['note'])
            if 'comment' in form.cleaned_data and form.cleaned_data['comment']:
                sheet_submission.set_assign_comment(form.cleaned_data['comment'])
            else:
                sheet_submission.set_assign_comment(None)

            sheet_submission.save()

            FormLogEntry.create(sheet_submission=sheet_submission, user=admin, category='ADMN',
                    description='Assigned sheet to %s.' % (formFiller.full_email()))

            # create an alternate URL, if necessary
            if not assign_to_sfu_account:
                SheetSubmissionSecretUrl.objects.create(sheet_submission=sheet_submission)
            # send email
            if formFiller.email() != admin.email():
                sheet_submission.email_assigned(request, admin, formFiller)

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Assigned form sheet %s (%i) to %s") % (sheet_submission.sheet, sheet_submission.sheet_id, sheet_submission.filler.identifier()),
                related_object=sheet_submission)
            l.save()
            messages.success(request, 'Sheet assigned.')
            return HttpResponseRedirect(reverse('onlineforms:admin_list_all'))

        # collect dictionary of frequent fillers of each form, for convenience links
        frequent_fillers = ((s, SheetSubmission.objects.filter(sheet__original=s.original)
                         .exclude(filler__sfuFormFiller=None)
                         .values('filler__sfuFormFiller', 'filler__sfuFormFiller__emplid', 'filler__sfuFormFiller__first_name', 'filler__sfuFormFiller__last_name')
                         .annotate(count=Count('filler'))
                         .order_by('-count')[:5])
                        for s in sheets)
        frequent_fillers = dict(((s.id,[
                {'emplid': d['filler__sfuFormFiller__emplid'],
                 'name': conditional_escape(d['filler__sfuFormFiller__first_name'] + ' ' + d['filler__sfuFormFiller__last_name'])}
                for d in ssc])
             for s, ssc in frequent_fillers))

        context = {'form': form, 'form_submission': form_submission, 'assign_to_sfu_account': assign_to_sfu_account,
                   'frequent_fillers': mark_safe(json.dumps(frequent_fillers)), 'has_sheets': sheets.count() > 0}
        return render(request, "onlineforms/admin/admin_assign.html", context)


@requires_formgroup()
def admin_assign_any_nonsfu(request):
    return _admin_assign_any(request, assign_to_sfu_account=False)
@requires_formgroup()
def admin_assign_any(request, assign_to_sfu_account=True):
    return _admin_assign_any(request, assign_to_sfu_account=True)

def _admin_assign_any(request, assign_to_sfu_account=True):
    """
    Give a form('s initial sheet) to a user
    """
    with django.db.transaction.atomic():
        admin = get_object_or_404(Person, userid=request.user.username)

        if assign_to_sfu_account:
            form = AdminAssignFormForm(data=request.POST or None,
                query_set=Form.objects.filter(active=True, owner__in=request.formgroups).exclude(initiators='NON'))
        else:
            form = AdminAssignFormForm_nonsfu(data=request.POST or None,
                query_set=Form.objects.filter(active=True, owner__in=request.formgroups, initiators='ANY'))

        if request.method == 'POST' and form.is_valid():
            # get the person to assign too
            if assign_to_sfu_account:
                assignee = form.cleaned_data['assignee']
                formFiller = _userToFormFiller(assignee)
            else:
                nonSFUFormFiller = form.save()
                formFiller = FormFiller.objects.create(nonSFUFormFiller=nonSFUFormFiller)
            # create new form submission with a blank sheet submission
            form = form.cleaned_data['form']
            form_submission = FormSubmission.objects.create(form=form,
                                initiator=formFiller,
                                owner=form.owner,
                                status='NEW')
            sheet_submission = SheetSubmission.objects.create(form_submission=form_submission,
                sheet=form.initial_sheet,
                filler=formFiller)
            sheet_submission.set_assigner(admin)
            sheet_submission.save()
            FormLogEntry.create(sheet_submission=sheet_submission, user=admin, category='ADMN',
                    description='Assigned initial sheet to %s.' % (formFiller.full_email()))

            # create an alternate URL, if necessary
            if not assign_to_sfu_account:
                SheetSubmissionSecretUrl.objects.create(sheet_submission=sheet_submission)
            # send email
            if formFiller.email() != admin.email():
                sheet_submission.email_assigned(request, admin, formFiller)
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                description=("Assigned form %s to %s") % (form, sheet_submission.filler.identifier()),
                related_object=sheet_submission)
            l.save()
            messages.success(request, 'Form assigned.')
            return HttpResponseRedirect(reverse('onlineforms:admin_list_all'))

        context = {'form': form, 'assign_to_sfu_account': assign_to_sfu_account}
        return render(request, "onlineforms/admin/admin_assign_any.html", context)

@requires_formgroup()
def admin_change_owner(request, form_slug, formsubmit_slug):
    with django.db.transaction.atomic():
        admin = get_object_or_404(Person, userid=request.user.username)
        form_submission = get_object_or_404(FormSubmission, form__slug=form_slug, slug=formsubmit_slug,
                                            owner__in=request.formgroups)

        # Can assign to groups in Units where I'm in a FormGroup, or and subunits of them.
        unit_ids = set(FormGroupMember.objects.filter(person=admin).values_list('formgroup__unit', flat=True))
        sub_unit_ids = Unit.sub_unit_ids(unit_ids, by_id=True)
        allowed_groups = FormGroup.objects.filter(unit__id__in=sub_unit_ids).exclude(id=form_submission.owner_id)

        if request.method == 'POST':
            form = ChangeOwnerForm(data=request.POST, queryset=allowed_groups)
            if form.is_valid():
                new_g = form.cleaned_data['new_group']
                form_submission.owner = new_g
                form_submission.email_notify_new_owner(request, admin)
                form_submission.save()

                FormLogEntry.create(form_submission=form_submission, user=admin, category='ADMN',
                    description='Gave ownership to group "%s".' % (new_g.name,))

                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Gave ownership of form sub %s; %s to %s" % (form_submission.form.slug, form_submission.slug, new_g.name)),
                    related_object=form_submission)
                l.save()
                messages.success(request, 'Form given to group "%s".' % (new_g.name))
                return HttpResponseRedirect(reverse('onlineforms:admin_list_all'))

        else:
            form = ChangeOwnerForm(queryset=allowed_groups)

        context = {'form': form, 'formsub': form_submission}
        return render(request, "onlineforms/admin/admin_change_owner.html", context)


@requires_formgroup()
def admin_return_sheet(request, form_slug, formsubmit_slug, sheetsubmit_slug):
    with django.db.transaction.atomic():
        admin = get_object_or_404(Person, userid=request.user.username)
        form_submission = get_object_or_404(FormSubmission, form__slug=form_slug, slug=formsubmit_slug,
                                            owner__in=request.formgroups)
        sheet_submission = get_object_or_404(SheetSubmission, form_submission=form_submission, slug=sheetsubmit_slug)

        # There shouldn't be a link to this anymore, but either way, we don't allow returning of the initial
        # sheet.  Since we can't assign an initial sheet, we shouldn't return it, which is the same thing.
        # This caused problems with the auto-cleanup code where there were suddenly open initial sheets that
        # where older than our cutoff period:
        if sheet_submission.sheet.is_initial:
            messages.error(request, 'You cannot return the initial sheet.')
            return HttpResponseRedirect(reverse('onlineforms:view_submission',
                                                kwargs={'form_slug': form_slug, 'formsubmit_slug': formsubmit_slug}))

        if request.method == 'POST':
            form = AdminReturnForm(data=request.POST)
            if form.is_valid():
                reason = form.cleaned_data['reason']
                sheet_submission.status = 'WAIT'
                sheet_submission.set_return_reason(reason)
                sheet_submission.save()

                FormLogEntry.create(sheet_submission=sheet_submission, user=admin, category='ADMN',
                    description='Returned sheet to %s.' % (sheet_submission.filler.full_email(),))

                sheet_submission.email_returned(request, admin)

                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Returned sheet submission %s to %s" % (sheet_submission, sheet_submission.filler)),
                    related_object=sheet_submission)
                l.save()
                messages.success(request, 'Sheet returned to %s.' % (sheet_submission.filler.name()))
                return HttpResponseRedirect(reverse('onlineforms:view_submission', kwargs={'form_slug': form_slug, 'formsubmit_slug': formsubmit_slug}))

        else:
            form = AdminReturnForm()

        context = {'sheetsub': sheet_submission, 'formsub': form_submission, 'form': form}
        return render(request, "onlineforms/admin/admin_return_sheet.html", context)

def _userToFormFiller(user):
    try:
        form_filler = FormFiller.objects.get(sfuFormFiller=user)
    except ObjectDoesNotExist:
        form_filler = FormFiller.objects.create(sfuFormFiller=user)
    except MultipleObjectsReturned:
        #  It shouldn't be possible, but there are occasionally Formfillers that have the same sfuFormFiller.  Since
        #  this isn't enforced at the database level, deal with it this way until we clean it up and/or enforce it.
        form_filler = FormFiller.objects.filter(sfuFormFiller=user).first()
    return form_filler


@requires_formgroup()
def admin_completed(request):
    forms = Form.objects.filter(owner__in=request.formgroups).order_by('unit__slug', 'title').select_related('unit')
    context = {'forms': forms}
    return render(request, "onlineforms/admin/admin_completed.html", context)

@requires_formgroup()
def admin_completed_form(request, form_slug):
    form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    formsubs = FormSubmission.objects.filter(form=form, status='DONE') \
           .select_related('initiator__sfuFormFiller', 'initiator__nonSFUFormFiller') \
           .annotate(last_sheet_dt=Max('sheetsubmission__completed_at'))

    context = {'form': form, 'formsubs': formsubs}
    return render(request, "onlineforms/admin/admin_completed_form.html", context)

@requires_formgroup()
def summary_csv(request, form_slug):
    form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    response = HttpResponse(content_type='text/csv;charset=utf-8')
    response['Content-Disposition'] = 'inline; filename="%s-summary.csv"' % (form_slug)
    writer = csv.writer(response)
    # A special case for one particular form, for now.
    if form_slug == 'mse-mse-ta-application-mse-graduate-students':
        headers, data = form.all_submission_summary_special(recurring_sheet_slug='instructor-approval-7')
    # All the SEE hiring forms are duplicates of one another with a different title.  They all also need
    # this special handling.  Their recurring sheet is all titled the same.
    #
    # If we're going to use this code path any more than this, then a better suggestion would be to store the recurring
    # sheet in the config of the form, look for said config variable, and just call the alternate method if it exists.
    elif form_slug in ['apsc-see-lecturer-electrical-and-electronics', 'apsc-see-lecturer-engineering-and-design-2',
                       'apsc-see-lecturer-writing-ethics-and-economics',
                       'apsc-see-researcher-materials-for-energy-systems', 'apsc-see-researcher-thermo-fluids']:
        headers, data = form.all_submission_summary_special(recurring_sheet_slug='initial-scoring')
    #  This one is just slightly different (the sheet we want to be recurring is named differently.)
    elif form_slug == 'apsc-see-professor-of-professional-practice':
        headers, data = form.all_submission_summary_special(recurring_sheet_slug='support-for-interview')
    else:
        headers, data = form.all_submission_summary()
    writer.writerow(headers)
    for row in data:
        writer.writerow(row)
    return response


@requires_formgroup()
def pending_summary_csv(request, form_slug):
    form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    response = HttpResponse(content_type='text/csv;charset=utf-8')
    response['Content-Disposition'] = 'inline; filename="%s-pending_summary.csv"' % form_slug
    writer = csv.writer(response)
    # A special case for one particular form, for now.
    if form_slug == 'mse-mse-ta-application-mse-graduate-students':
        headers, data = form.all_submission_summary_special(statuses=['PEND'],
                                                            recurring_sheet_slug='instructor-approval-7')

    # All the SEE hiring forms are duplicates of one another with a different title.  They all also need
    # this special handling.  Their recurring sheet is all titled the same.
    #
    # If we're going to use this code path any more than this, then a better suggestion would be to store the recurring
    # sheet in the config of the form, look for said config variable, and just call the alternate method if it exists.
    elif form_slug in ['apsc-see-lecturer-electrical-and-electronics', 'apsc-see-lecturer-engineering-and-design-2',
                       'apsc-see-lecturer-writing-ethics-and-economics',
                       'apsc-see-researcher-materials-for-energy-systems', 'apsc-see-researcher-thermo-fluids']:
        headers, data = form.all_submission_summary_special(statuses=['PEND'],
                                                            recurring_sheet_slug='initial-scoring')
    #  This one is just slightly different (the sheet we want to be recurring is named differently.)
    elif form_slug == 'apsc-see-professor-of-professional-practice':
        headers, data = form.all_submission_summary_special(statuses=['PEND'],
                                                            recurring_sheet_slug='support-for-interview')
    else:
        headers, data = form.all_submission_summary(statuses=['PEND'])
    writer.writerow(headers)
    for row in data:
        writer.writerow(row)
    return response


@requires_formgroup()
def waiting_summary_csv(request, form_slug):
    form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    response = HttpResponse(content_type='text/csv;charset=utf-8')
    response['Content-Disposition'] = 'inline; filename="%s-waiting_summary.csv"' % form_slug
    writer = csv.writer(response)
    # A special case for one particular form, for now.
    if form_slug == 'mse-mse-ta-application-mse-graduate-students':
        headers, data = form.all_submission_summary_special(statuses=['WAIT'],
                                                            recurring_sheet_slug='instructor-approval-7')

    # All the SEE hiring forms are duplicates of one another with a different title.  They all also need
    # this special handling.  Their recurring sheet is all titled the same.
    #
    # If we're going to use this code path any more than this, then a better suggestion would be to store the recurring
    # sheet in the config of the form, look for said config variable, and just call the alternate method if it exists.
    elif form_slug in ['apsc-see-lecturer-electrical-and-electronics', 'apsc-see-lecturer-engineering-and-design-2',
                       'apsc-see-lecturer-writing-ethics-and-economics',
                       'apsc-see-researcher-materials-for-energy-systems', 'apsc-see-researcher-thermo-fluids']:
        headers, data = form.all_submission_summary_special(statuses=['WAIT'],
                                                            recurring_sheet_slug='initial-scoring')
    #  This one is just slightly different (the sheet we want to be recurring is named differently.)
    elif form_slug == 'apsc-see-professor-of-professional-practice':
        headers, data = form.all_submission_summary_special(statuses=['WAIT'],
                                                            recurring_sheet_slug='support-for-interview')

    else:
        headers, data = form.all_submission_summary(statuses=['WAIT'])
    writer.writerow(headers)
    for row in data:
        writer.writerow(row)
    return response


#######################################################################
# Creating/editing forms

@requires_formgroup()
def list_all(request):
    with django.db.transaction.atomic():
        forms = Form.objects.filter(owner__in=request.formgroups, active=True)
        if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
            form_id = request.POST['form_id']
            forms = forms.filter(id=form_id)
            if forms:
                form = forms[0]
                form.delete()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Deleted form %s.") % (form,),
                    related_object=form)
                l.save()
                messages.success(request, 'Removed the Form')
            return HttpResponseRedirect(reverse('onlineforms:list_all'))
        else:
            form = FormForm()
            context = {'form': form, 'forms': forms}
        return render(request, 'onlineforms/manage_forms.html', context)


@requires_formgroup()
def new_form(request):
    with django.db.transaction.atomic():
        group_choices = [(fg.id, str(fg)) for fg in request.formgroups]
        if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'add':
            form = NewFormForm(request.POST)
            form.fields['owner'].choices = group_choices
            if form.is_valid():
                f = form.save(commit=False)
                # use FormGroup's unit as the Form's unit
                f.unit = f.owner.unit
                f.save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Created form %s.") % (f,),
                    related_object=f)
                l.save()
                return HttpResponseRedirect(reverse('onlineforms:view_form', kwargs={'form_slug':f.slug }))
        else:
            form = NewFormForm()
            form.fields['owner'].choices = group_choices
        return render(request, 'onlineforms/new_form.html', {'form': form})


@requires_form_admin_by_slug()
def view_form(request, form_slug):
    form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    sheets = Sheet.objects.filter(form=form, active=True).order_by('order')
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
        sheet_id = request.POST['sheet_id']
        sheets = Sheet.objects.filter(id=sheet_id, form=form)
        if sheets:
            sheet = sheets[0]
            sheet.delete()
            messages.success(request, 'Removed the sheet "%s".' % (sheet.title))
           
        return HttpResponseRedirect(
            reverse('onlineforms:view_form', kwargs={'form_slug':form.slug }))

    form_url = request.build_absolute_uri(reverse('onlineforms:sheet_submission_initial', kwargs={'form_slug': form_slug}))
    context = {'form': form, 'sheets': sheets, 'form_url': form_url}
    return render(request, "onlineforms/view_form.html", context)       


@requires_form_admin_by_slug()
def edit_form(request, form_slug):
    with django.db.transaction.atomic():
        owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
        group_choices = [(fg.id, str(fg)) for fg in request.formgroups]

        if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'edit':
            form = FormForm(request.POST, instance=owner_form)
            form.fields['owner'].choices = group_choices
            if form.is_valid():
                f = form.save(commit=False)
                # use FormGroup's unit as the Form's unit
                f.unit = f.owner.unit
                f.save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Edited form %s.") % (f,),
                    related_object=f)
                l.save()
                return HttpResponseRedirect(reverse('onlineforms:view_form', kwargs={'form_slug': owner_form.slug}))
        else:
            form = FormForm(instance=owner_form)
            form.fields['owner'].choices = group_choices

        context = {'form': form, 'owner_form': owner_form}
        return render(request, 'onlineforms/edit_form.html', context)


@requires_form_admin_by_slug()
def new_sheet(request, form_slug):
    with django.db.transaction.atomic():
        owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
        if request.method == 'POST':
            form = SheetForm(request.POST)
            if form.is_valid():
                sheet = Sheet.objects.create(title=form.cleaned_data['title'], form=owner_form, can_view=form.cleaned_data['can_view'])
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Created form sheet %s.") % (sheet,),
                    related_object=sheet)
                l.save()
                messages.success(request, 'Successfully created the new sheet "%s' % form.cleaned_data['title'])
                return HttpResponseRedirect(
                    reverse('onlineforms:edit_sheet', kwargs={'form_slug': form_slug, 'sheet_slug': sheet.slug}))
        else:
            initial = {}
            other_sheets = Sheet.objects.filter(form=owner_form, active=True).count()
            if other_sheets == 0:
                initial['title'] = owner_form.title
                initial['can_view'] = 'NON'
            form = SheetForm(initial=initial)

        context = {'form': form, 'owner_form': owner_form}
        return render(request, "onlineforms/new_sheet.html", context)

@requires_form_admin_by_slug()
def preview_form(request, form_slug):
    owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    sheet_forms = []

    for owner_sheet in Sheet.objects.filter(form=owner_form, active=True):
        form = DynamicForm(owner_sheet.title)
        fields = Field.objects.filter(sheet=owner_sheet, active=True).order_by('order')
        form.fromFields(fields)
        sheet_forms.append(form)

    context = {'owner_form': owner_form, 'sheet_forms': sheet_forms}
    return render(request, "onlineforms/preview_form.html", context)

@requires_form_admin_by_slug()
def preview_sheet(request, form_slug, sheet_slug):
    owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
    owner_sheet = get_object_or_404(Sheet, slug=sheet_slug, form=owner_form)

    form = DynamicForm(owner_sheet.title)
    fields = Field.objects.filter(sheet=owner_sheet, active=True).order_by('order')
    form.fromFields(fields)

    context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet}
    return render(request, "onlineforms/preview_sheet.html", context)

@requires_form_admin_by_slug()
def edit_sheet(request, form_slug, sheet_slug):
    with django.db.transaction.atomic():
        owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
        owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
        fields = Field.objects.filter(sheet=owner_sheet, active=True).order_by('order')
        # Non Ajax way to reorder activity, please also see reorder_activity view function for ajax way to reorder
        order = None
        field_slug = None
        if 'order' in request.GET:
            order = request.GET['order']
        if 'field_slug' in request.GET:
            field_slug = request.GET['field_slug']
        if order and field_slug:
            reorder_sheet_fields(fields, field_slug, order)
            return HttpResponseRedirect(
                reverse('onlineforms:edit_sheet', kwargs={'form_slug': form_slug, 'sheet_slug': sheet_slug}))

        # check if they are deleting a field from the sheet
        if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
            field_id = request.POST['field_id']
            fields = Field.objects.filter(id=field_id, sheet=owner_sheet)
            if fields:
                # need a new version of the form since we're making a change:
                owner_sheet = owner_sheet.safe_save()
                field = fields[0]
                field = Field.objects.get(sheet=owner_sheet, original=field.original) # get field on new version, not old
                field.active = False
                field.save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Removed form field %s.") % (field,),
                    related_object=field)
                l.save()
                messages.success(request, 'Removed the field %s.' % (field.label))
            return HttpResponseRedirect(
                reverse('onlineforms:edit_sheet', kwargs={'form_slug': owner_form.slug, 'sheet_slug': owner_sheet.slug}))

        # construct a form from this sheets fields
        form = DynamicForm(owner_sheet.title)
        form.fromFields(fields)

        # a list of dictionaries containing the field model object(for editing) and the field form object(for display)
        modelFormFields = []
        for (counter, field) in enumerate(form):
            field.type =  FIELD_TYPES[fields[counter].fieldtype]
            modelFormFields.append({'modelField': fields[counter], 'formField': field})

        context = {'owner_form': owner_form, 'owner_sheet': owner_sheet, 'form': form, 'fields': modelFormFields}
        return render(request, "onlineforms/edit_sheet.html", context)

@requires_form_admin_by_slug()
def reorder_field(request, form_slug, sheet_slug):
    """
    Ajax way to reorder activity.
    This ajax view function is called in the edit_sheet page.
    """
    with django.db.transaction.atomic():
        form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
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
    with django.db.transaction.atomic():
        owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
        owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
        #owner_field = get_object_or_404(Field, slug=field_slug)

        if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'edit':
            form = EditSheetForm(request.POST, instance=owner_sheet)
            if form.is_valid():
                new_sheet = owner_sheet.safe_save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Edited form sheet %s.") % (new_sheet,),
                    related_object=new_sheet)
                l.save()
                return HttpResponseRedirect(reverse('onlineforms:edit_sheet',
                    kwargs={'form_slug': owner_form.slug, 'sheet_slug': new_sheet.slug}))
        else:
            form = EditSheetForm(instance=owner_sheet)

        context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet}
        return render(request, 'onlineforms/edit_sheet_info.html', context)


@requires_form_admin_by_slug()
def new_field(request, form_slug, sheet_slug):
    with django.db.transaction.atomic():
        owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
        owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)

        invalid_submission = False

        if request.method == 'POST' and 'type' in request.POST:
            ftype = request.POST['type']
            TypeModel = FIELD_TYPE_MODELS[ftype]
            custom_config = _clean_config(request.POST)
            field = TypeModel(config=custom_config)
            form = field.make_config_form()

            if form.is_valid():
                new_sheet = owner_sheet.safe_save()
                f = Field.objects.create(label=form.cleaned_data['label'],
                        sheet=new_sheet,
                        fieldtype=ftype,
                        config=custom_config,
                        active=True,
                        original=None, )
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Created form field %s.") % (f,),
                    related_object=f)
                l.save()
                messages.success(request, 'Successfully created the new field \'%s\'' % form.cleaned_data['label'])

                return HttpResponseRedirect(
                        reverse('onlineforms:edit_sheet', args=(form_slug, new_sheet.slug)))
                
            # Fall-through to redisplay form with errors
            invalid_submission = True

        if (request.method == 'GET' and 'type' in request.GET) or invalid_submission == True:
            # have selected the field type: now configure the field.
            if request.method == 'GET':
                # these are set above in invalid_submission fallthrough case
                ftype = request.GET['type']
                TypeModel = FIELD_TYPE_MODELS[ftype]
                field = TypeModel()
                field.config = None # force form to behave as new, not as nothing-useful-submitted
                form = field.make_config_form()

            need_choices = field.choices
            type_description = FIELD_TYPES[ftype]
            
            # ... unless we don't have to configure. Then don't.
            if not field.configurable:
                new_sheet = owner_sheet.safe_save()
                f = Field.objects.create(label='',
                    sheet=new_sheet,
                    fieldtype=ftype,
                    config={},
                    active=True,
                    original=None, )
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Created form field %s.") % (f,),
                    related_object=f)
                l.save()
                messages.success(request, 'Successfully created a new field')

                return HttpResponseRedirect(
                    reverse('onlineforms:edit_sheet', args=(form_slug, new_sheet.slug)))
            
            context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet, 'choices': need_choices, 'ftype': ftype, 'type_description': type_description}
            return render(request, 'onlineforms/new_field.html', context)

        else:
            # need to select field type
            form = FieldForm()
            context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet}
            return render(request, 'onlineforms/new_field_select.html', context)


def _clean_config(config):
    irrelevant_fields = ['csrfmiddlewaretoken', 'next_section', 'type_name']
    clean_config = dict((key, value) for (key, value) in config.items() if key not in irrelevant_fields)
    clean_config['required'] = 'required' in clean_config

    return clean_config


@requires_form_admin_by_slug()
def edit_field(request, form_slug, sheet_slug, field_slug):
    with django.db.transaction.atomic():
        owner_form = get_object_or_404(Form, slug=form_slug, owner__in=request.formgroups)
        owner_sheet = get_object_or_404(Sheet, form=owner_form, slug=sheet_slug)
        field = get_object_or_404(Field, sheet=owner_sheet, slug=field_slug)

        ftype = FIELD_TYPE_MODELS[field.fieldtype]
        need_choices = ftype().choices

        if request.POST:
            clean_config = _clean_config(request.POST)
            form = ftype(config=clean_config).make_config_form()
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
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Edited form field %s.") % (new_field,),
                    related_object=new_field)
                l.save()
                messages.success(request, 'Successfully updated the field "%s"' % form.cleaned_data['label'])

                return HttpResponseRedirect(
                    reverse('onlineforms:edit_sheet', args=(new_sheet.form.slug, new_sheet.slug)))

        else:
            if not ftype.configurable:
                return HttpResponseRedirect(
                    reverse('onlineforms:edit_sheet', args=(form_slug, sheet_slug)))
            form = FIELD_TYPE_MODELS[field.fieldtype](config=field.config).make_config_form()

        context = {'form': form, 'owner_form': owner_form, 'owner_sheet': owner_sheet, 'field': field,
                   'choices': need_choices}

        return render(request, 'onlineforms/edit_field.html', context)


#######################################################################
# Submitting sheets

def index(request):
    form_groups = None
    sheet_submissions = None
    participated = None
    if request.user.is_authenticated:
        loggedin_user = get_object_or_404(Person, userid=request.user.username)
        forms = Form.objects.filter(active=True).exclude(initiators='NON').order_by('unit__name', 'title')
        forms = [form for form in forms if not form.unlisted()]
        other_forms = []
        sheet_submissions = SheetSubmission.objects.filter(filler=_userToFormFiller(loggedin_user)) \
            .exclude(status='DONE').exclude(status='REJE')
        # get all the form groups the logged in user is a part of
        form_groups = FormGroup.objects.filter(members=loggedin_user)
        # If the user is authenticated, see if they have forms that are done in which they participated.
        participated = SheetSubmission.objects.filter(filler=_userToFormFiller(loggedin_user))\
            .exclude(form_submission__initiator=_userToFormFiller(loggedin_user)).count() > 0

    else:
        forms = Form.objects.filter(active=True, initiators='ANY').order_by('unit__name', 'title')
        forms = [form for form in forms if not form.unlisted()]
        other_forms = Form.objects.filter(active=True, initiators='LOG')
        other_forms = [form for form in other_forms if not form.unlisted()]

    form_admin = Role.objects_fresh.filter(role__in=['ADMN', 'FORM'], person__userid=request.user.username).count() > 0

    context = {'forms': forms, 'other_forms': other_forms, 'sheet_submissions': sheet_submissions,
               'form_groups': form_groups, 'form_admin': form_admin, 'participated': participated}
    return render(request, 'onlineforms/submissions/forms.html', context)


@login_required()
def login(request):
    #  This is a dummy view to put in the email reminders.  This ensures that people are actually logged in
    #  if they click on the link in the reminder, thus making sure they see their forms.
    return HttpResponseRedirect(reverse('onlineforms:index'))


@login_required()
def participated_in(request):
    loggedin_user = get_object_or_404(Person, userid=request.user.username)
    participated = SheetSubmission.objects.filter(filler=_userToFormFiller(loggedin_user))\
        .exclude(form_submission__initiator=_userToFormFiller(loggedin_user))
    return render(request, 'onlineforms/submissions/participated.html', {'participated': participated})


is_displayable_sheet_sub = Q(status__in=["DONE","REJE"]) | Q(sheet__is_initial=True)
def _readonly_sheets(form_submission, current_sheetsub=None):
    """
    Collect sheet subs and other info to display this form submission.
    """
    sheet_submissions = SheetSubmission.objects \
            .filter(form_submission=form_submission) \
            .filter(is_displayable_sheet_sub) \
            .order_by('completed_at')

    # If we passed in a current sheet submission, we may want to see submissions for a form we were involved in, or we
    # have limited access to the current sheet and the initial sheet only.  Based on the passed in sheet sub, we can
    # decide what sheet subs should be displayed.
    if current_sheetsub:
        # If you could view all sheetsubs at the time you got this one, see everything up to it.
        if current_sheetsub.sheet.can_view == 'ALL':
            sheet_submissions = [sheetsub for sheetsub in sheet_submissions if sheetsub.completed_at <=
                                 current_sheetsub.given_at or sheetsub == current_sheetsub or sheetsub.sheet.is_initial]

        # If you should only see the current and initial sheet, deal with that that here.
        elif current_sheetsub.sheet.can_view == 'INI':
            sheet_submissions = [sheetsub for sheetsub in sheet_submissions if sheetsub == current_sheetsub or
                                 sheetsub.sheet.is_initial]
        else:
        # Otherwise, sheetsub status was "NON", see only this sheet
            sheet_submissions = [current_sheetsub]


    sheet_sub_html = []
    for sheet_sub in sheet_submissions:
        # get html from field submissions
        field_submissions = FieldSubmission.objects.filter(sheet_submission=sheet_sub)
        fields = []
        for field_sub in field_submissions:
            field = FIELD_TYPE_MODELS[field_sub.field.fieldtype](field_sub.field.config)
            field.fieldtype = field_sub.field.fieldtype
            if field.configurable:
                field.label = field.config['label']
                field.html = field.to_html(field_sub)

            fields.append(field)
        sheet_sub_html.append((sheet_sub, fields))
    return sheet_sub_html


def _formsubmission_find_and_authz(request, form_slug, formsubmit_slug, file_id=None):
    """
    If this user is allowed to view this FormSubmission, return it, or None if not.
    Also returns is_advisor, boolean as appropriate.
    """
    # can access if in owning formgroup
    formgroups = FormGroup.objects.filter(members__userid=request.user.username)
    form_submissions = FormSubmission.objects.filter(form__slug=form_slug, slug=formsubmit_slug,
                                        owner__in=formgroups)
    is_advisor = False
    if not form_submissions:
        # advisors can access relevant completed forms
        advisor_roles = Role.objects_fresh.filter(person__userid=request.user.username, role='ADVS')
        units = set(r.unit for r in advisor_roles)
        units = Unit.sub_units(units)
        form_submissions = FormSubmission.objects.filter(form__slug=form_slug, slug=formsubmit_slug,
                                        form__unit__in=units, form__advisor_visible=True)
        is_advisor = True

    if file_id:
        # expanded permissions for files: filler of this and other sheets.
        fsfs = FieldSubmissionFile.objects.filter(
                                field_submission__sheet_submission__form_submission__slug=formsubmit_slug,
                                id=file_id).select_related('field_submission__sheet_submission__form_submission',
                                                           'field_submission__sheet_submission__sheet')
        if fsfs:
            fsf = fsfs[0]
            formsub = fsf.field_submission.sheet_submission.form_submission
            sheetsub = fsf.field_submission.sheet_submission
            this_sub = SheetSubmission.objects.filter(form_submission=formsub,
                    id=sheetsub.id,
                    filler__sfuFormFiller__userid=request.user.username)
            if this_sub:
                # this is the filler of this sheet: they can see it.
                form_submissions = [formsub]

            later_sheets = SheetSubmission.objects.filter(form_submission=formsub,
                    filler__sfuFormFiller__userid=request.user.username,
                    given_at__gte=sheetsub.completed_at,
                    sheet__can_view='ALL')

            # Another edge case:  The sheetsub with the files is the initial sheet, but it got modified later on,
            # so its completed date is later than the sheet we are using.  If this is the initial sheet, and the
            # user has filled in any other sheets for this form where they could see all, let them get to the file
            # as well.  Also, if the user had access to another sheet where the permission was to just view the initial
            # sheet, they should also be able to download the file.
            filled_sheets_by_user = None
            if sheetsub.sheet.is_initial:
                filled_sheets_by_user = \
                    SheetSubmission.objects.filter(form_submission=formsub,
                                                   filler__sfuFormFiller__userid=request.user.username,
                                                   sheet__can_view__in=['ALL', 'INI'])

            if later_sheets or filled_sheets_by_user:
                # this is the filler of a later sheet who can view the other parts or this is the initial sheet and
                # this filler has filled other sheets and can view other parts.
                form_submissions = [formsub]

    if not form_submissions:
        return None, None

    return form_submissions[0], is_advisor

@login_required
def file_field_download(request, form_slug, formsubmit_slug, file_id, action):
    form_submission, _ = _formsubmission_find_and_authz(request, form_slug, formsubmit_slug, file_id=file_id)
    if not form_submission:
        raise Http404
    file_sub =  get_object_or_404(FieldSubmissionFile,
                                  field_submission__sheet_submission__form_submission=form_submission,
                                  id=file_id)
    file_path = file_sub.file_attachment.file.name
    filename = os.path.basename(file_path)

    file_sub.file_attachment.file.open()
    response = HttpResponse(file_sub.file_attachment.file, content_type=file_sub.file_mediatype)
    
    if action == 'download':
        disposition = 'download'
    else:
        disposition = 'inline'
    
    response['Content-Disposition'] = disposition + '; filename="' + filename + '"'
    return response


@login_required
def view_submission(request, form_slug, formsubmit_slug):
    with django.db.transaction.atomic():
        form_submission, is_advisor = _formsubmission_find_and_authz(request, form_slug, formsubmit_slug)
        if not form_submission:
            raise Http404

        sheet_submissions = _readonly_sheets(form_submission)
        can_admin = not is_advisor and form_submission.status != 'DONE'
        waiting_sheets = SheetSubmission.objects.filter(form_submission=form_submission, status='WAIT')

        if request.method == 'POST' and can_admin:
            close_form = CloseFormForm(advisor_visible=form_submission.form.advisor_visible, data=request.POST, prefix='close')
            if close_form.is_valid():
                admin = Person.objects.get(userid=request.user.username)
                email = False
                email_cc = None
                if 'summary' in close_form.cleaned_data:
                    form_submission.set_summary(close_form.cleaned_data['summary'])
                if 'email' in close_form.cleaned_data:
                    form_submission.set_emailed(close_form.cleaned_data['email'])
                    email = close_form.cleaned_data['email']
                if 'email_cc' in close_form.cleaned_data:
                    form_submission.set_email_cc(close_form.cleaned_data['email_cc'])
                    email_cc = close_form.cleaned_data['email_cc']


                for ss in waiting_sheets:
                    ss.status = 'REJE'
                    ss.set_reject_reason('Withdrawn when form was closed by %s.' % (admin.userid))
                    ss.save()
                
                form_submission.set_closer(admin.id)
                form_submission.status = 'DONE'
                form_submission.save()

                if email:
                    form_submission.email_notify_completed(request, admin, email_cc=email_cc)
                    messages.success(request, 'Form submission marked as completed; initiator informed by email.')
                    FormLogEntry.create(form_submission=form_submission, user=admin, category='ADMN',
                        description='Marked form completed (and emailed to notify user).')
                else:
                    messages.success(request, 'Form submission marked as completed.')
                    FormLogEntry.create(form_submission=form_submission, user=admin, category='ADMN',
                        description='Marked form completed (but user was not emailed through system).')

                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                    description=("Marked form submission %s done.") % (form_submission,),
                    related_object=form_submission)
                l.save()
                return HttpResponseRedirect(reverse('onlineforms:admin_list_all'))

        elif can_admin:
            close_form = CloseFormForm(advisor_visible=form_submission.form.advisor_visible, prefix='close')
        else:
            close_form = None

        can_advise = Role.objects_fresh.filter(person__userid=request.user.username, role='ADVS').count() > 0

        logentries = FormLogEntry.objects.filter(form_submission=form_submission) \
                .exclude(category__in=['AUTO', 'MAIL', 'SAVE']) \
                .select_related('user', 'externalFiller', 'sheet_submission__sheet')

        # combine (SheetSubmission, [FieldSubmissions]) and (FormLogEntry, _) objects into a unified chronology
        formsub_activity = list(sheet_submissions) + [(le, 'FormLogEntry') for le in logentries]
        formsub_activity.sort(key=lambda a: a[0].completed_at)

        context = {
                   'form': form_submission.form,
                   'form_sub': form_submission,
                   'formsub_activity': formsub_activity,
                   'form_slug': form_slug,
                   'formsubmit_slug': formsubmit_slug,
                   'is_advisor': is_advisor,
                   'can_admin': can_admin,
                   'can_advise': can_advise,
                   'close_form': close_form,
                   'waiting_sheets': waiting_sheets,
                   }
        return render(request, 'onlineforms/admin/view_partial_form.html', context)


@requires_form_admin_by_slug()
def reject_sheet_admin(request, form_slug, formsubmit_slug, sheet_slug, sheetsubmit_slug):
    sheetsub = get_object_or_404(SheetSubmission, sheet__form__slug=form_slug,
                                 form_submission__slug=formsubmit_slug, sheet__slug=sheet_slug, slug=sheetsubmit_slug,
                                 form_submission__owner__in=request.formgroups)
    return _reject_sheet(request, sheetsub, from_admin=True)


@requires_form_admin_by_slug()
def reject_sheet_via_url_admin(request, secret_url, form_slug):
    # It looks like the form_slug parameter is not needed, but it is needed for the decorator
    secret = get_object_or_404(SheetSubmissionSecretUrl, key=secret_url)
    return _reject_sheet(request, secret.sheet_submission, from_admin=True)


@login_required
def reject_sheet_subsequent(request, form_slug, formsubmit_slug, sheet_slug, sheetsubmit_slug):
    sheetsub = get_object_or_404(SheetSubmission, sheet__form__slug=form_slug,
        form_submission__slug=formsubmit_slug, sheet__slug=sheet_slug, slug=sheetsubmit_slug,
        filler__sfuFormFiller__userid=request.user.username)
    return _reject_sheet(request, sheetsub)


def reject_sheet_via_url(request, secret_url):
    secret = get_object_or_404(SheetSubmissionSecretUrl, key=secret_url)
    return _reject_sheet(request, secret.sheet_submission)


def _reject_sheet(request, sheetsub, from_admin=False):
    with django.db.transaction.atomic():
        if request.method != 'POST':
            return ForbiddenResponse(request)

        if 'reject_reason' in request.POST:
            sheetsub.set_reject_reason(request.POST['reject_reason'])
        sheetsub.status = 'REJE'
        sheetsub.save()

        if from_admin:
            admin = get_object_or_404(Person, userid=request.user.username)
            FormLogEntry.create(sheet_submission=sheetsub, user=admin, category='ADMN',
                                description='Rejected sheet.')

        elif sheetsub.sheet.is_initial:
            FormLogEntry.create(sheet_submission=sheetsub, filler=sheetsub.filler, category='FILL',
                    description='Discarded initial sheet.')
            fs = sheetsub.form_submission
            fs.status = 'REJE'
            fs.save()
        else:
            FormLogEntry.create(sheet_submission=sheetsub, filler=sheetsub.filler, category='FILL',
                    description='Returned sheet without completing.')
            sheetsub.email_submitted(request, rejected=True)

        l = LogEntry(userid=request.user.username,
            description=("Rejected sheet %s") % (sheetsub),
            related_object=sheetsub)
        l.save()
        if from_admin:
            messages.success(request, 'Sheet rejected')
        elif sheetsub.sheet.is_initial:
            messages.success(request, 'Form discarded.')
        else:
            messages.success(request, 'Sheet rejected and returned to the admins.')
        return HttpResponseRedirect(reverse('onlineforms:index'))


def sheet_submission_via_url(request, secret_url):
    """
    Sheet submission from a user who has been sent a secret URL
    """
    sheet_submission_secret_url = get_object_or_404(SheetSubmissionSecretUrl, key=secret_url)
    sheet_submission_object = sheet_submission_secret_url.sheet_submission
    sheet = sheet_submission_object.sheet
    form_submission = sheet_submission_object.form_submission
    form = form_submission.form
    alternate_url = reverse('onlineforms:sheet_submission_via_url', kwargs={'secret_url': secret_url})
    return _sheet_submission(request, form_slug=form.slug, formsubmit_slug=form_submission.slug,
                             sheet_slug=sheet.slug, sheetsubmit_slug=sheet_submission_object.slug,
                             alternate_url=alternate_url)


def sheet_submission_initial(request, form_slug):
    """
    Submission from a user who is initiating a new form submission
    """
    return _sheet_submission(request, form_slug=form_slug)

def sheet_submission_subsequent(request, form_slug, formsubmit_slug, sheet_slug, sheetsubmit_slug):
    """
    Submission by a user who is returning to a partially-completed sheet submission
    """
    return _sheet_submission(request, form_slug=form_slug, formsubmit_slug=formsubmit_slug,
                             sheet_slug=sheet_slug, sheetsubmit_slug=sheetsubmit_slug)

@retry_transaction()
def _sheet_submission(request, form_slug, formsubmit_slug=None, sheet_slug=None, sheetsubmit_slug=None, alternate_url=None):
    with django.db.transaction.atomic():
        owner_form = get_object_or_404(Form, slug=form_slug)
        this_path = request.get_full_path()
        readonly = False
        
        # if no one can fill out this form, stop right now
        if owner_form.initiators == "NON" and not formsubmit_slug:
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
        if request.user.is_authenticated:
            try:
                loggedin_user = ensure_person_from_userid(request.user.username)
                
            # If the user is authenticated through CAS, and logged in, but is *not* a Person in our system,
            # *and* the SIMS reporting DB is down, we'll get a problem here.  Don't ask how we know.  Let's deal
            # with it.
            except SIMSProblem:
                messages.error(request, 'The SIMS database is not allowing us to verify your identity.  Please try '
                                        'again later.  Your submission has NOT been saved.')
                return HttpResponseRedirect(reverse('onlineforms:index'))

            if loggedin_user is None:
                return ForbiddenResponse(request, "The userid '%s' isn't known to this system. If this is a 'role' account, please log in under your primary SFU userid. Otherwise, please contact %s for assistance." % (request.user.username, help_email(request)))
            logentry_userid = loggedin_user.userid
            nonSFUFormFillerForm = None
        else:
            loggedin_user = None
            logentry_userid = ""
            # make a form for non sfu people, unless they have an alternate_url
            # in which case the form filler object would already have been created
            nonSFUFormFillerForm = NonSFUFormFillerForm() if not alternate_url else None

        # a field -> field submission lookup
        field_submission_dict = {}
        # previously filled sheets to display
        filled_sheets = []
        # get the submission objects(if they exist) and create the form
        if formsubmit_slug and sheetsubmit_slug:
            form_submission = get_object_or_404(FormSubmission, form=owner_form, slug=formsubmit_slug)
            sheet_submission = get_object_or_404(SheetSubmission, sheet__original=sheet.original,
                                                 form_submission=form_submission, slug=sheetsubmit_slug)
            sheet = sheet_submission.sheet # revert to the old version that the user was working with.
            # check if this sheet has already been filled
            if sheet_submission.status in ["DONE", "REJE"]:
                messages.info(request, 'That form sheet has already been completed and submitted. It cannot be edited further.')
                filled_sheets = _readonly_sheets(form_submission, sheet_submission)
                # Set correct flags.  Don't set the sheet to None, as we need it in the template for some info.
                # instead, set the readonly flag.
                form = None
                readonly = True

            # check that they can access this sheet
            formFiller = sheet_submission.filler
            if sheet_submission.filler.isSFUPerson():
                if not(formFiller.sfuFormFiller) or loggedin_user != formFiller.sfuFormFiller:
                    if request.user.is_authenticated:
                        return ForbiddenResponse(request)
                    else:
                        # not logged in: maybe they really are the filler and we need to know.
                        return login_redirect(request.path)
            # do we do need to do any checking for non sfu form fillers?  Only if we don't already have filled_sheets
            # which would mean that we are now viewing in read_only mode
            if not filled_sheets:
                form = DynamicForm(sheet.title)
                form.fromFields(sheet.fields, sheet_submission.field_submissions)

            # populate the field -> fieldSubmission lookup
            for field_submission in sheet_submission.field_submissions:
                field_submission_dict[field_submission.field] = field_submission

            # get previously filled in sheet's data
            if not readonly:
                #  Most of the logic here is in the next method.  If you can see everything, just pass in the form_sub.
                if sheet.can_view == 'ALL':
                    filled_sheets = _readonly_sheets(form_submission)
                #  If you pass in the sheet_sub, more checking will get done to gauge permissions based on the given
                # sheet.
                elif sheet.can_view == 'INI':
                    filled_sheets = _readonly_sheets(form_submission, sheet_submission)

        else:
            # make sure we are allowed to initiate this form
            if not loggedin_user and owner_form.initiators != "ANY":
                return redirect_to_login(request.path)
            form = DynamicForm(sheet.title)
            form.fromFields(sheet.fields)
            form_submission = None
            sheet_submission = None
            formFiller = None

        if request.method == 'POST' and ('save' in request.POST or 'submit' in request.POST):
            #  We may be submitting/saving this from a browser tab when the sheet/form has already been completed
            #  elsewhere.  In that case, the form object will be None, see line 1385.

            if not form:
                messages.warning(request, "Your content was NOT submitted, as the sheet was previously closed/submitted.  Someone may have done so while your browser tab was open on this sheet.")
                return HttpResponseRedirect(reverse('onlineforms:index'))

            # get the info from post
            if 'save' in request.POST:
                form.fromPostData(request.POST, request.FILES, ignore_required=True)
            elif 'submit' in request.POST:
                form.fromPostData(request.POST, request.FILES)

            if form.is_valid():
                # sheet is valid, lets get a form filler (if we don't already have one)
                if not formFiller:
                    # we don't have a form filler from above (could be initial sheet submission)
                    # if they provided a non-SFU form use that info, otherwise grab their logged in credentials
                    if 'add-nonsfu' in request.POST and sheet.is_initial and owner_form.initiators == "ANY":
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
                        else:
                            formFiller = None
                    elif loggedin_user:
                        formFiller = _userToFormFiller(loggedin_user)
                    else:
                        # they didn't provide nonsfu info and they are not logged in
                        # (or the sheet doesn't allow non-SFU people to fill it in)
                        context = {'owner_form': owner_form,
                                   'error_msg': "You must have a SFU account and be logged in to fill out this form."}
                        return render(request, 'onlineforms/submissions/sheet_submission.html', context)

                if formFiller:
                    # we have a form filler, the data is valid, create the formsubmission and sheetsubmission objects if necessary
                    if not(form_submission):
                        # create the form submission
                        form_submission = FormSubmission(form=owner_form, initiator=formFiller, owner=owner_form.owner, status='NEW')
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
                    for name, field in list(form.fields.items()):
                        # a field can be skipped if we are saving (not submitting) the form, and it is not in the cleaned data
                        if not('submit' in request.POST) or str(name) in form.cleaned_data:
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
                                # remove old files if asked
                                if request.POST.get(str(name)+"-clear", False):
                                    old_fsf = FieldSubmissionFile.objects.filter(field_submission=fieldSubmission)
                                    for fsf in old_fsf:
                                        fsf.file_attachment.delete()
                                        fsf.delete()

                                # save the new submission
                                if str(name) in request.FILES:
                                    new_file = request.FILES[str(name)]
                                    old_fsf = FieldSubmissionFile.objects.filter(field_submission=fieldSubmission)
                                    if old_fsf:
                                        new_file_submission = old_fsf[0]
                                        #new_file_submission.file_attachment.delete()
                                    else:
                                        new_file_submission = FieldSubmissionFile(field_submission=fieldSubmission)

                                    new_file_submission.file_attachment = new_file
                                    new_file_submission.file_mediatype = new_file.content_type
                                    new_file_submission.save()

                    # cleanup for each submit-mode
                    if 'save' in request.POST:
                        # refill the form with the new data
                        form.fromFields(sheet.fields, sheet_submission.get_field_submissions(refetch=True))
                        # don't redirect, show the form with errors(if they exist) but notify them that info was saved

                        if alternate_url:
                            access_url = alternate_url
                        elif not formFiller.isSFUPerson():
                            # if they aren't accessing via an alternate url, they aren't a SFU account,
                            # and they are saving then we need to create a alternate url for them to use
                            secret_url = SheetSubmissionSecretUrl(sheet_submission=sheet_submission)
                            secret_url.save()
                            #LOG EVENT#
                            l = LogEntry(userid=logentry_userid,
                                description=("URL created for sheet submission %s of form %s by %s") % (sheet_submission, owner_form.title, formFiller.email()),
                                related_object=secret_url)
                            l.save()
                            # email them the URL
                            sheet_submission.email_started(request)
                            access_url = reverse('onlineforms:sheet_submission_via_url', kwargs={'secret_url': secret_url.key})
                        else:
                            sheet_submission.email_started(request)
                            access_url = reverse('onlineforms:sheet_submission_subsequent', kwargs={
                                'form_slug': owner_form.slug,
                                'formsubmit_slug': form_submission.slug,
                                'sheet_slug': sheet.slug,
                                'sheetsubmit_slug': sheet_submission.slug})

                        FormLogEntry.create(sheet_submission=sheet_submission, filler=formFiller, category='SAVE',
                                description='Saved sheet without submitting.')

                        messages.success(request, 'All fields without errors were saved. Use this page\'s URL to edit this submission in the future.')
                        return HttpResponseRedirect(access_url)
                    elif 'submit' in request.POST:
                        # all the fields have been submitted, this sheet is done
                        sheet_submission.status = 'DONE'
                        sheet_submission.save()
                        l = LogEntry(userid=logentry_userid,
                            description=("Sheet submission %s completed by %s") % (sheet_submission.slug, formFiller.email()),
                            related_object=sheet_submission)
                        l.save()

                        sheet_submission.email_submitted(request)

                        FormLogEntry.create(sheet_submission=sheet_submission, filler=formFiller, category='FILL',
                                description='Submitted sheet.')

                        if sheet.is_initial and sheet.form.autoconfirm():
                            sheet.form.email_confirm(formFiller)

                        messages.success(request, 'You have succesfully completed sheet %s of form %s.' % (sheet.title, owner_form.title))
                        return HttpResponseRedirect(reverse('onlineforms:index'))
                else:
                    messages.error(request, "Error in user data.")
            else:
                messages.error(request, "The form could not be submitted because of errors in the supplied data, please correct them and try again.")

        can_advise = Role.objects_fresh.filter(person__userid=request.user.username, role='ADVS').count() > 0

        context = {'owner_form': owner_form,
                   'sheet': sheet,
                   'form': form,
                   'form_submission': form_submission,
                   'sheet_submission': sheet_submission,
                   'filled_sheets': filled_sheets,
                   'alternate_url': alternate_url,
                   'nonSFUFormFillerForm': nonSFUFormFillerForm,
                   'this_path': this_path,
                   'can_advise': can_advise,
                   'readonly': readonly}
        return render(request, 'onlineforms/submissions/sheet_submission.html', context)
