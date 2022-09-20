from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from coredata.forms import RoleForm, UnitRoleForm, InstrRoleFormSet, MemberForm, PersonForm, TAForm, \
        UnitAddressForm, UnitForm, SemesterForm, SemesterWeekFormset, HolidayFormset, SysAdminSearchForm, \
        TemporaryPersonForm, CourseHomePageForm, OneOfferingForm, NewCombinedForm, AnyPersonForm, RoleAccountForm, \
        OffboardForm, EditPersonForm
from courselib.auth import requires_global_role, requires_role, requires_course_staff_by_slug, ForbiddenResponse, \
        has_formgroup, has_global_role
from courselib.search import get_query, find_userid_or_emplid
from coredata.models import Person, Semester, CourseOffering, Course, Member, Role, Unit, SemesterWeek, Holiday, \
    AnyPerson, FuturePerson, RoleAccount, CombinedOffering, UNIT_ROLES, ROLES, ROLE_DESCR, INSTR_ROLES, DISC_ROLES
from coredata import panel
from advisornotes.models import NonStudent
from onlineforms.models import FormGroup, FormGroupMember
from log.models import LogEntry
from coredata.models import LONG_LIVED_ROLES
from django.urls import reverse
from django.contrib import messages
from cache_utils.decorators import cached
from haystack.query import SearchQuerySet
import socket, json, datetime, os
import iso8601
from functools import reduce
from operator import itemgetter

@requires_global_role("SYSA")
def sysadmin(request):
    if 'usersearch' in request.GET:
        # user search
        form = SysAdminSearchForm(request.GET)
        if form.is_valid() and form.cleaned_data['user']:
            emplid = form.cleaned_data['user'].emplid
            return HttpResponseRedirect(reverse('sysadmin:user_summary', kwargs={'userid': emplid}))
    elif 'offeringsearch' in request.GET:
        # course offering search
        form = SysAdminSearchForm(request.GET)
        if form.is_valid() and form.cleaned_data['offering']:
            offering = form.cleaned_data['offering']
            return HttpResponseRedirect(reverse('sysadmin:offering_summary', kwargs={'course_slug': offering.slug}))
    else:
        form = SysAdminSearchForm()
    
    return render(request, 'coredata/sysadmin.html', {'form': form})


@requires_global_role("SYSA")
def role_list(request):
    """
    Display list of who has what role
    """
    roles = Role.objects_fresh.exclude(role="NONE").select_related('person', 'unit')

    return render(request, 'coredata/roles.html', {'roles': roles})


@requires_global_role("SYSA")
def expired_role_list(request):
    """
    Display long-lived roles that have accidentally expired
    """
    roles = Role.objects.filter(role__in=LONG_LIVED_ROLES, expiry__lt=datetime.date.today()).select_related('person', 'unit')

    return render(request, 'coredata/expired_roles.html', {'roles': roles})

@requires_global_role("SYSA")
def new_role(request, role=None):
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            r = form.save(commit=False)
            r.config['giver'] = request.user.username
            r.config['given_date'] = datetime.date.today().isoformat()
            r.save()
            messages.success(request, 'Added role %s for %s.' % (form.instance.get_role_display(), form.instance.person.name()))
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new role: %s as %s") % (form.instance.person.userid, form.instance.role),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse('sysadmin:role_list'))
    else:
        form = RoleForm(initial={'expiry': datetime.date.today() + datetime.timedelta(days=365)})

    return render(request, 'coredata/new_role.html', {'form': form})

@requires_global_role("SYSA")
def renew_role(request, role_id):
    if request.method != 'POST':
        return ForbiddenResponse(request)

    role = get_object_or_404(Role, pk=role_id)
    new_exp = datetime.date.today() + datetime.timedelta(days=365)
    role.expiry = new_exp
    role.save()

    messages.success(request, 'Renewed role for %s until %s.' % (role.person.name(), new_exp))
    # LOG EVENT#
    l = LogEntry(userid=request.user.username,
                 description=("renewed role: %s for %s in %s until %s") % (
                 role.get_role_display(), role.person.name(), role.unit, new_exp),
                 related_object=role.person)
    l.save()
    return HttpResponseRedirect(reverse('sysadmin:role_list'))

@requires_global_role("SYSA")
def delete_role(request, role_id):
    role = get_object_or_404(Role, pk=role_id)
    messages.success(request, 'Deleted role %s for %s.' % (role.get_role_display(), role.person.name()))
    #LOG EVENT#
    l = LogEntry(userid=request.user.username,
          description=("deleted role: %s for %s") % (role.get_role_display(), role.person.name()),
          related_object=role.person)
    l.save()
    
    role.delete()
    return HttpResponseRedirect(reverse('sysadmin:role_list'))



@requires_global_role("SYSA")
def unit_list(request):
    """
    Display list of all units
    """
    units = Unit.objects.all()
    return render(request, 'coredata/units.html', {'units': units})

@requires_global_role("SYSA")
def edit_unit(request, unit_slug=None):
    if unit_slug:
        unit = get_object_or_404(Unit, slug=unit_slug)
    else:
        unit = Unit()
    
    if request.method == 'POST':
        form = UnitForm(instance=unit, data=request.POST)
        if form.is_valid():
            unit.slug = None
            form.save()
            messages.success(request, 'Edited unit %s.' % (unit.name))
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited unit %s") % (form.instance.slug),
                  related_object=unit)
            l.save()
            return HttpResponseRedirect(reverse('sysadmin:unit_list'))
    else:
        form = UnitForm(instance=unit)
    
    context = {'form': form}
    return render(request, 'coredata/edit_unit.html', context)





@requires_global_role("SYSA")
def members_list(request):
    members = Member.objects.exclude(added_reason="AUTO").exclude(added_reason="CTA").exclude(added_reason="TAC") \
            .select_related('offering__semester')
    return render(request, 'coredata/members_list.html', {'members': members})


@requires_global_role("SYSA")
def edit_member(request, member_id=None):
    if member_id:
        member = get_object_or_404(Member, id=member_id)
    else:
        member = None

    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited membership: %s as %s in %s") % (form.instance.person.userid, form.instance.role, form.instance.offering),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse('sysadmin:members_list'))
    elif member_id:
        form = MemberForm(instance=member, initial={'person': member.person.userid})
    else:
        form = MemberForm()
    
    return render(request, 'coredata/edit_member.html', {'form': form, 'member': member})


@requires_global_role("SYSA")
def user_summary(request, userid):
    query = find_userid_or_emplid(userid)
    person = get_object_or_404(Person, query)

    if request.method == 'POST':
        from coredata.importer import import_person
        grad_data = 'import-grad' in request.POST
        person = import_person(person, commit=True, grad_data=grad_data)
        messages.success(request, 'Imported SIMS data for %s.' % (person.userid_or_emplid()))
    
    memberships = Member.objects.filter(person=person)
    roles = Role.objects_fresh.filter(person=person).exclude(role="NONE").select_related('unit')
    
    context = {'person': person, 'memberships': memberships, 'roles': roles}
    return render(request, "coredata/user_summary.html", context)


@requires_global_role("SYSA")
def user_config(request, userid):
    query = find_userid_or_emplid(userid)
    person = get_object_or_404(Person, query)
    if request.method == 'POST':
        form = EditPersonForm(request.POST, instance=person)
        if form.is_valid():
            form.save()
            # LOG EVENT #
            l = LogEntry(userid=request.user.username,
                  description=("person config edited: %s (%s)") % (form.instance.name(), form.instance.userid),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse('sysadmin:user_config', kwargs={'userid': person.emplid}))
    else:
        form = EditPersonForm(instance=person, initial={"email": person.config['email'] if 'email' in person.config else None,
                                                        "pref_first_name": person.config['pref_first_name'] if 'pref_first_name' in person.config else None})
    return render(request, "coredata/user_config.html", {'person': person, 'form': form})


@requires_global_role("SYSA")
def offering_summary(request, course_slug):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    
    staff = Member.objects.filter(offering=offering, role__in=['INST', 'TA'])
    
    context = {'offering': offering, 'staff': staff}
    return render(request, "coredata/offering_summary.html", context)


@requires_global_role("SYSA")
def new_person(request):
    if request.method == 'POST':
        form = PersonForm(request.POST)
        if form.is_valid():
            form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new person added: %s (%s)") % (form.instance.name(), form.instance.userid),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse('sysadmin:sysadmin'))
    else:
        form = PersonForm()

    return render(request, 'coredata/new_person.html', {'form': form})


# semester object management

@requires_global_role("SYSA")
def semester_list(request):
    semesters = Semester.objects.all()
    return render(request, 'coredata/semester_list.html', {'semesters': semesters})

@requires_global_role("SYSA")
def edit_semester(request, semester_name=None):
    if semester_name:
        semester = get_object_or_404(Semester, name=semester_name)
        newsem = False
    else:
        semester = Semester()
        newsem = True
    
    if request.method == 'POST':
        form = SemesterForm(instance=semester, prefix='sem', data=request.POST)
        week_formset = SemesterWeekFormset(queryset=SemesterWeek.objects.filter(semester=semester), prefix='week', data=request.POST)
        holiday_formset = HolidayFormset(queryset=Holiday.objects.filter(semester=semester), prefix='holiday', data=request.POST)
        if form.is_valid() and week_formset.is_valid() and holiday_formset.is_valid():
            sem = form.save()
            
            weeks = week_formset.save(commit=False)
            for week in weeks:
                week.semester = sem
                week.save()

            holidays = holiday_formset.save(commit=False)
            for holiday in holidays:
                holiday.semester = sem
                holiday.save()
            
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited semester %s") % (sem.name),
                  related_object=sem)
            l.save()
            messages.success(request, 'Edited semester %s.' % (sem.name))
            return HttpResponseRedirect(reverse('sysadmin:semester_list', kwargs={}))
    else:
        form = SemesterForm(instance=semester, prefix='sem')
        week_formset = SemesterWeekFormset(queryset=SemesterWeek.objects.filter(semester=semester), prefix='week')
        holiday_formset = HolidayFormset(queryset=Holiday.objects.filter(semester=semester), prefix='holiday')

    context = {'semester': semester, 'form': form, 'newsem': newsem,
               'week_formset': week_formset, 'holiday_formset': holiday_formset}
    return render(request, 'coredata/edit_semester.html', context)


# combined sections admin

@requires_global_role("SYSA")
def combined_offerings(request):
    combined = CombinedOffering.objects.all()
    new_form = OneOfferingForm()
    context = {
        'combined': combined,
        'new_form': new_form,
    }
    return render(request, 'coredata/combined_offerings.html', context)


def _new_fake_class_nbr(semester):
    # largest class_nbr in production is 47348. Assuming that >65536 can be reserved as fakes.
    from django.db.models import Max
    max_offering = CourseOffering.objects.filter(semester=semester).aggregate(Max('class_nbr'))['class_nbr__max']
    max_combined = CombinedOffering.objects.filter(semester=semester).aggregate(Max('class_nbr'))['class_nbr__max']

    nbr = 65536
    if max_offering:
        nbr = max(nbr, max_offering)
    if max_combined:
        nbr = max(nbr, max_combined)

    return nbr+1

@requires_global_role("SYSA")
def new_combined(request):
    offering_id = request.GET.get('offering', None)
    offering = get_object_or_404(CourseOffering, id=offering_id)
    if request.method == 'POST':
        form = NewCombinedForm(request.POST)
        if form.is_valid():
            combined = form.save(commit=False)
            combined.semester = offering.semester
            combined.crse_id = offering.crse_id
            combined.class_nbr = _new_fake_class_nbr(combined.semester)
            combined.save()
            combined.offerings.add(offering)
            combined.create_combined_offering()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created combined offering %i with %s") % (combined.id, offering.slug),
                  related_object=combined)
            l.save()
            messages.success(request, 'Created combined offering.')
            return HttpResponseRedirect(reverse('sysadmin:combined_offerings', kwargs={}))
    else:
        # set up creation form from the offering given
        initial = {
            'subject': offering.subject,
            'number': offering.number,
            'section': 'X100',
            'component': offering.component,
            'instr_mode': offering.instr_mode,
            'owner': offering.owner,
            'title': offering.title,
            'campus': offering.campus,
        }
        form = NewCombinedForm(initial=initial)

    context = {
        'form': form,
    }
    return render(request, 'coredata/edit_combined.html', context)

@requires_global_role("SYSA")
def add_combined_offering(request, pk):
    combined = get_object_or_404(CombinedOffering, pk=pk)
    if request.method == 'POST':
        form = OneOfferingForm(request.POST)
        if form.is_valid():
            offering = form.cleaned_data['offering']
            if offering in combined.offerings.all():
                messages.error(request, 'That offering is already in the combined section.')
            else:
                combined.offerings.add(offering)
                combined.create_combined_offering()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("added %s to combined offering %i") % (offering.slug, combined.id),
                      related_object=combined)
                l.save()
                messages.success(request, 'Added offering.')
                return HttpResponseRedirect(reverse('sysadmin:combined_offerings', kwargs={}))
    else:
        form = OneOfferingForm()

    context = {
        'form': form,
    }
    return render(request, 'coredata/add_combined_offering.html', context)



@requires_global_role("SYSA")
def admin_panel(request):
    if 'content' in request.GET:
        if request.GET['content'] == 'deploy_checks':
            passed, failed = panel.deploy_checks(request=request)
            return render(request, 'coredata/admin_panel_tab.html', {'passed': passed, 'failed': failed})
        elif request.GET['content'] == 'settings_info':
            data = panel.settings_info()
            return render(request, 'coredata/admin_panel_tab.html', {'settings_data': data})
        elif request.GET['content'] == 'psinfo':
            data = panel.ps_info()
            return render(request, 'coredata/admin_panel_tab.html', {'psinfo': data})
        elif request.GET['content'] == 'email':
            user = Person.objects.get(userid=request.user.username)
            return render(request, 'coredata/admin_panel_tab.html', {'email': user.email()})
        elif request.GET['content'] == 'celery':
            data = panel.celery_info()
            return render(request, 'coredata/admin_panel_tab.html', {'celery': data})
        elif request.GET['content'] == 'tasks':
            return render(request, 'coredata/admin_panel_tab.html', {'tasks': True})
        elif request.GET['content'] == 'request':
            import pprint
            return render(request, 'coredata/admin_panel_tab.html', {'the_request': pprint.pformat(request.__dict__)})
        elif request.GET['content'] == 'git':
            git = {}
            git['branch'] = panel.git_branch().decode('utf8')
            git['revision'] = panel.git_revision().decode('utf8')
            return render(request, 'coredata/admin_panel_tab.html', {'git':git})
        elif request.GET['content'] == 'pip':
            data = panel.pip_info()
            return render(request, 'coredata/admin_panel_tab.html', {'pip': data})
        elif request.GET['content'] == 'csrpt':
            data = panel.csrpt_info()
            return render(request, 'coredata/admin_panel_tab.html', {'csrpt': data})
        elif request.GET['content'] == 'environ':
            environ = [(k,v) for k,v in os.environ.items()]
            environ.sort()
            return render(request, 'coredata/admin_panel_tab.html', {'environ': environ})
        elif request.GET['content'] == 'throw':
            raise RuntimeError('This is a deliberately-thrown exception to test exception-handling in the system. It can be ignored.')
        elif request.GET['content'] == 'slow':
            import time
            t = int(request.GET.get('t', '25'))
            time.sleep(t)
            resp = render(request, 'coredata/admin_panel_tab.html', {})
            if 'okay' in request.GET:
                resp.slow_okay = True
            return resp
    elif request.method == 'POST':
        if 'email' in request.POST:
            email = request.POST['email']
            success, res = panel.send_test_email(email)
            if success:
                messages.success(request, res)
            else:
                messages.error(request, res)
        elif 'tasks' in request.POST:
            if 'daily' in request.POST:
                from coredata.tasks import import_task
                import_task.apply_async()
                messages.success(request, 'Daily import task started.')
            elif 'visits' in request.POST:
                from advisornotes.tasks import program_info_for_advisorvisits
                program_info_for_advisorvisits.apply_async()
                messages.success(request, 'Advisor visit task started.')
            elif 'grad' in request.POST:
                from coredata.tasks import import_grads
                from grad.tasks import update_statuses_to_current
                update_statuses_to_current.apply_async()
                import_grads.apply_async()
                messages.success(request, 'Grad update and import tasks started.')

    context = {
        'loadavg': os.getloadavg()
    }
    return render(request, 'coredata/admin_panel.html', context)


# Methods for managing AnyPersons

@requires_global_role("SYSA")
def list_anypersons(request):
    anypersons = AnyPerson.objects.all()
    context = {'anypersons': anypersons}
    return render(request, 'coredata/any_persons.html', context)


@requires_global_role("SYSA")
def delete_anyperson(request, anyperson_id):
    anyperson = get_object_or_404(AnyPerson, pk=anyperson_id)
    if request.method == 'POST':
        anyperson.delete()
        messages.success(request, 'Deleted anyperson for %s' % anyperson)
        l = LogEntry(userid=request.user.username,
                     description="deleted anyperson: %s" % anyperson,
                     related_object=anyperson)
        l.save()
    return HttpResponseRedirect(reverse('sysadmin:list_anypersons'))


@requires_global_role("SYSA")
def add_anyperson(request):
    if request.method == 'POST':
        form = AnyPersonForm(request.POST)
        if form.is_valid():
            ap = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'AnyPerson %s was created.' % ap
                                 )
            l = LogEntry(userid=request.user.username,
                         description="added anyperson: %s" % ap,
                         related_object=ap
                         )
            l.save()

            return HttpResponseRedirect(reverse('sysadmin:list_anypersons'))
    else:
        form = AnyPersonForm()

    return render(request, 'coredata/new_anyperson.html', {'form': form})


@requires_global_role("SYSA")
def edit_anyperson(request, anyperson_id):
    anyperson = get_object_or_404(AnyPerson, pk=anyperson_id)
    if request.method == 'POST':
        form = AnyPersonForm(request.POST, instance=anyperson)
        if form.is_valid():
            ap = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'AnyPerson for %s was edited.' % ap
                                 )
            l = LogEntry(userid=request.user.username,
                         description="edited anyperson: %s" % ap,
                         related_object=ap
                         )
            l.save()

            return HttpResponseRedirect(reverse('sysadmin:list_anypersons'))
    else:
        initial_values = {}
        if anyperson.person:
            initial_values['person'] = anyperson.person.emplid
        if anyperson.future_person:
            initial_values['future_person'] = anyperson.future_person_id
        if anyperson.role_account:
            initial_values['role_account'] = anyperson.role_account_id
        form = AnyPersonForm(instance=anyperson, initial=initial_values)

    return render(request, 'coredata/edit_anyperson.html', {'form': form, 'anyperson_id': anyperson_id})


@requires_global_role("SYSA")
def delete_empty_anypersons(request):
    if request.method == 'POST':
        res = AnyPerson.delete_empty_anypersons()
        messages.add_message(request,
                             messages.SUCCESS,
                             'Deleted %s empty AnyPersonn(s).' % str(res)
                             )

        return HttpResponseRedirect(reverse('sysadmin:list_anypersons'))


@requires_global_role("SYSA")
def list_futurepersons(request):
    futurepersons = FuturePerson.objects.all()
    context = {'futurepersons': futurepersons}
    return render(request, 'coredata/future_persons.html', context)


@requires_global_role("SYSA")
def edit_futureperson(request, futureperson_id):
    return HttpResponseRedirect(reverse('faculty:edit_futureperson', kwargs={'futureperson_id': futureperson_id,
                                                                                   'from_admin': 1}))


@requires_global_role("SYSA")
def delete_futureperson(request, futureperson_id):
    if request.method == 'POST':
        futureperson = FuturePerson.objects.get(pk=futureperson_id)
        futureperson.delete()
        messages.success(request, 'Deleted futureperson %s' % futureperson)
        l = LogEntry(userid=request.user.username,
                     description="deleted futureperson: %s" % futureperson,
                     related_object=futureperson)
        l.save()
    return HttpResponseRedirect(reverse('sysadmin:list_futurepersons'))

@requires_global_role("SYSA")
def add_futureperson(request):
    from faculty.forms import FuturePersonForm
    if request.method == 'POST':
        form = FuturePersonForm(request.POST)
        if form.is_valid():
            new_future_person = form.save(commit=False)
            new_future_person.set_email(form.cleaned_data.get('email'))
            new_future_person.set_gender(form.cleaned_data.get('gender'))
            new_future_person.set_sin(form.cleaned_data.get('sin'))
            new_future_person.set_birthdate(form.cleaned_data.get('birthdate'))
            new_future_person.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'FuturePerson %s was edited.' % new_future_person
                                 )
            l = LogEntry(userid=request.user.username,
                         description="Added FuturePerson: %s" % new_future_person,
                         related_object=new_future_person
                         )
            l.save()
            return HttpResponseRedirect(reverse('sysadmin:list_futurepersons'))

    else:
        form = FuturePersonForm()
    return render(request, 'coredata/new_futureperson.html', {'form': form})

@requires_global_role("SYSA")
def view_futureperson(request, futureperson_id):
    return HttpResponseRedirect(reverse('faculty:view_futureperson', kwargs={'futureperson_id': futureperson_id,
                                                                                   'from_admin': 1}))

@requires_global_role("SYSA")
def list_roleaccounts(request):
    roleaccounts = RoleAccount.objects.all()
    context = {'roleaccounts': roleaccounts}
    return render(request, 'coredata/role_accounts.html', context)

@requires_global_role("SYSA")
def delete_roleaccount(request, roleaccount_id):
    roleaccount = RoleAccount.objects.get(pk=roleaccount_id)
    if request.method == 'POST':
        roleaccount.delete()
        messages.success(request, 'Deleted roleaccount %s' % roleaccount)
        l = LogEntry(userid=request.user.username,
                     description="deleted roleaccount: %s" % roleaccount,
                     related_object=roleaccount)
        l.save()
    return HttpResponseRedirect(reverse('sysadmin:list_roleaccounts'))

@requires_global_role("SYSA")
def edit_roleaccount(request, roleaccount_id):
    roleaccount = get_object_or_404(RoleAccount, pk=roleaccount_id)
    if request.method == 'POST':
        form = RoleAccountForm(request.POST, instance=roleaccount)
        if form.is_valid():
            ra = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Role Account %s was edited.' % ra
                                 )
            l = LogEntry(userid=request.user.username,
                         description="edited roleaccount: %s" % ra,
                         related_object=ra
                         )
            l.save()

            return HttpResponseRedirect(reverse('sysadmin:list_roleaccounts'))
    else:
        form = RoleAccountForm(instance=roleaccount)

    return render(request, 'coredata/edit_roleaccount.html', {'form': form, 'roleaccount_id': roleaccount_id})

@requires_global_role("SYSA")
def add_roleaccount(request):
    if request.method == 'POST':
        form = RoleAccountForm(request.POST)
        if form.is_valid():
            ra = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'added roleaccount %s' % ra
                                 )
            l = LogEntry(userid=request.user.username,
                         description="added roleaccount: %s" % ra,
                         related_object=ra
                         )
            l.save()

            return HttpResponseRedirect(reverse('sysadmin:list_roleaccounts'))
    else:
        form = RoleAccountForm()

    return render(request, 'coredata/new_roleaccount.html', {'form': form})

# views to let instructors manage TAs

@requires_course_staff_by_slug
def manage_tas(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    longform = False
    if not Member.objects.filter(offering=course, person__userid=request.user.username, role="INST"):
        # only instructors can manage TAs
        return ForbiddenResponse(request, "Only instructors can manage TAs")
    
    if request.method == 'POST' and 'action' in request.POST and request.POST['action']=='add':
        form = TAForm(offering=course, data=request.POST)
        if form.non_field_errors():
            # have an unknown userid
            longform = True
        elif form.is_valid():
            userid = form.cleaned_data['userid']
            if not Person.objects.filter(userid=userid) \
                    and form.cleaned_data['fname'] and form.cleaned_data['lname']:
                # adding a new person: handle that.
                eid = 1
                # search for an unused temp emplid
                while True:
                    emplid = "%09i" % (eid)
                    if not Person.objects.filter(emplid=emplid):
                        break
                    eid += 1
                p = Person(first_name=form.cleaned_data['fname'], pref_first_name=form.cleaned_data['fname'], last_name=form.cleaned_data['lname'], middle_name='', userid=userid, emplid=emplid)
                p.save()

            else:
                p = Person.objects.get(userid=userid)

            m = Member(person=p, offering=course, role="TA", credits=0, career="NONS", added_reason="TAIN")
            m.save()
                
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("TA added by instructor: %s for %s") % (userid, course),
                  related_object=m)
            l.save()
            messages.success(request, 'Added %s as a TA.' % (p.name()))
            return HttpResponseRedirect(reverse('offering:manage_tas', kwargs={'course_slug': course.slug}))
            

    elif request.method == 'POST' and 'action' in request.POST and request.POST['action']=='del':
        userid = request.POST['userid']
        ms = Member.objects.filter(person__userid=userid, offering=course, role="TA", added_reason="TAIN")
        if ms:
            m = ms[0]
            m.role = "DROP"
            m.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("TA removed by instructor: %s for %s") % (userid, course),
                  related_object=m)
            l.save()
            messages.success(request, 'Removed %s as a TA.' % (m.person.name()))
        return HttpResponseRedirect(reverse('offering:manage_tas', kwargs={'course_slug': course.slug}))

    else:
        form = TAForm(offering=course)

    tas = Member.objects.filter(role="TA", offering=course)
    context = {'course': course, 'form': form, 'tas': tas, 'longform': longform}
    return render(request, 'coredata/manage_tas.html', context)


# views for departmental admins to manage permissions

@requires_role("ADMN")
def unit_admin(request):
    """
    Unit admin front page
    """
    return render(request, 'coredata/unit_admin.html', {'units': Unit.sub_units(request.units)})


@requires_role("ADMN")
def unit_role_list(request):
    """
    Display list of who has what role (for department admins)
    """
    roles = Role.objects_fresh.filter(unit__in=Unit.sub_units(request.units), role__in=UNIT_ROLES)
    return render(request, 'coredata/unit_roles.html', {'roles': roles})


@requires_role("ADMN")
def new_unit_role(request):
    role_choices = [(r,ROLES[r]) for r in UNIT_ROLES]
    # Make the form more readable by sorting by role long name.
    role_choices.sort(key=itemgetter(1))
    unit_choices = [(u.id, str(u)) for u in Unit.sub_units(request.units)]
    if request.method == 'POST':
        form = UnitRoleForm(request.POST)
        form.fields['role'].choices = role_choices
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            r = form.save(commit=False)
            r.config['giver'] = request.user.username
            r.config['given_date'] = datetime.date.today().isoformat()
            r.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new role: %s as %s in %s") % (form.instance.person.userid, form.instance.role, form.instance.unit),
                  related_object=form.instance)
            l.save()
            messages.success(request, "Added role: %s as %s in %s." % (r.person, r.get_role_display(), r.unit.name))
            return HttpResponseRedirect(reverse('admin:unit_role_list'))
    else:
        form = UnitRoleForm(initial={'expiry': datetime.date.today() + datetime.timedelta(days=365)})
        form.fields['role'].choices = role_choices
        form.fields['unit'].choices = unit_choices
        
    context = {'form': form, 'UNIT_ROLES': UNIT_ROLES, 'ROLE_DESCR': ROLE_DESCR}
    return render(request, 'coredata/new_unit_role.html', context)

@requires_role("ADMN")
def offboard_unit(request):
    if request.method == 'POST':
        form = OffboardForm(request.POST)
        if form.is_valid():
            person = form.cleaned_data['person']
            delete_roles = form.cleaned_data['delete_roles']
            delete_formgroups = form.cleaned_data['delete_formgroups']
            roles = Role.objects_fresh.filter(person=person, unit__in=Unit.sub_units(request.units),
                                              role__in=UNIT_ROLES + DISC_ROLES)
            groups = FormGroup.objects.filter(members=person, unit__in=Unit.sub_units(request.units))
            if delete_roles:
                for role in roles:
                    role.delete()
                    l = LogEntry(userid=request.user.username,
                                 description=("Deleted role: %s in %s via offboarding form.") % (role, role.unit),
                                 related_object=role)
                    l.save()
                    messages.success(request, "Removed role %s as %s in %s." % (person, role.get_role_display(), role.unit.label))
            if delete_formgroups:
                for group in groups:
                    member = FormGroupMember.objects.get(person=person, formgroup=group)
                    member.delete()
                    l = LogEntry(userid=request.user.username,
                                 description=("Removed %s from form group %s (%i) via offboarding form.") % (
                                              person.userid_or_emplid(), group, group.id),
                                 related_object=group)
                    l.save()
                    messages.success(request, "Removed %s from formgroup %s" % (person, group))
            return HttpResponseRedirect(reverse('admin:unit_role_list'))
    else:
        form = OffboardForm()
    return render(request, 'coredata/offboard_unit.html', {'form': form})


@requires_role("ADMN")
def roles(request, emplid):
    person = get_object_or_404(Person, emplid=emplid)
    roles = Role.objects_fresh.filter(person=person, unit__in=Unit.sub_units(request.units), role__in=UNIT_ROLES)
    groups = FormGroup.objects.filter(members=person, unit__in=Unit.sub_units(request.units))
    data = {}
    if roles:
        data['roles'] = []
    if groups:
        data['formgroups'] = []
    for role in roles:
        data['roles'].append('%s in %s' % (role.get_role_display(), role.unit.name))
    for group in groups:
        data['formgroups'].append(str(group))
    response = HttpResponse(content_type='application/json')
    json.dump(data, response, indent=1)
    return response

@requires_role("ADMN")
def renew_unit_roles_list(request):
    """
    Display list of who has what role
    """
    allow_renewal = datetime.timedelta(days=182)+datetime.date.today()
    roles = Role.objects_fresh.filter(unit__in=Unit.sub_units(request.units), role__in=UNIT_ROLES, expiry__lt=allow_renewal)

    return render(request, 'coredata/renew_unit_roles.html', {'roles': roles})

@requires_role("ADMN")
def renew_unit_roles(request, id=None):
    """
    Renew Multiple Roles
    """
    if request.method == 'POST':
        to_renew = request.POST.getlist('renewals')
        if to_renew == []:
            messages.error(request, 'Please select at least one role to renew.')
        else: 
            for role_id in to_renew:
                role = get_object_or_404(Role, pk=role_id, unit__in=Unit.sub_units(request.units), role__in=UNIT_ROLES)
                new_exp = datetime.date.today() + datetime.timedelta(days=365)
                role.expiry = new_exp
                role.save()

                messages.success(request, 'Renewed role for %s until %s.' % (role.person.name(), new_exp))
                # LOG EVENT#
                l = LogEntry(userid=request.user.username,
                            description=("renewed role: %s for %s in %s until %s") % (
                            role.get_role_display(), role.person.name(), role.unit, new_exp),
                            related_object=role.person)
                l.save()
    return HttpResponseRedirect(reverse('admin:renew_unit_roles_list'))


@requires_role("ADMN")
def renew_unit_role(request, role_id):
    if request.method != 'POST':
        return ForbiddenResponse(request)

    role = get_object_or_404(Role, pk=role_id, unit__in=Unit.sub_units(request.units), role__in=UNIT_ROLES)
    new_exp = datetime.date.today() + datetime.timedelta(days=365)
    role.expiry = new_exp
    role.save()

    messages.success(request, 'Renewed role for %s until %s.' % (role.person.name(), new_exp))
    # LOG EVENT#
    l = LogEntry(userid=request.user.username,
                 description=("renewed role: %s for %s in %s until %s") % (
                 role.get_role_display(), role.person.name(), role.unit, new_exp),
                 related_object=role.person)
    l.save()

    return HttpResponseRedirect(reverse('admin:unit_role_list'))

@requires_role("ADMN")
def delete_unit_role(request, role_id):
    if request.method != 'POST':
        return ForbiddenResponse(request)

    role = get_object_or_404(Role, pk=role_id, unit__in=Unit.sub_units(request.units), role__in=UNIT_ROLES)
    messages.success(request, 'Deleted role %s for %s.' % (role.get_role_display(), role.person.name()))
    # LOG EVENT#
    l = LogEntry(userid=request.user.username,
                 description=("deleted role: %s for %s in %s") % (
                 role.get_role_display(), role.person.name(), role.unit),
                 related_object=role.person)
    l.save()

    role.delete()
    return HttpResponseRedirect(reverse('admin:unit_role_list'))


@requires_role('ADMN')
def unit_address(request, unit_slug):
    unit = get_object_or_404(Unit, slug=unit_slug)
    if unit not in Unit.sub_units(request.units):
        return ForbiddenResponse(request, "Not an admin for this unit")
    
    if request.method == 'POST':
        form = UnitAddressForm(data=request.POST, unit=unit)
        if form.is_valid():
            #print form.cleaned_data
            form.copy_to_unit()
            unit.save()
            
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("updated contact info for %s") % (unit.label),
                  related_object=unit)
            l.save()
            return HttpResponseRedirect(reverse('admin:unit_admin'))
    else:
        form = UnitAddressForm(unit=unit)
    context = {'unit': unit, 'form': form}
    return render(request, "coredata/unit_address.html", context)


@requires_role('ADMN')
def missing_instructors(request, unit_slug):
    unit = get_object_or_404(Unit, slug=unit_slug)
    if unit not in Unit.sub_units(request.units):
        return ForbiddenResponse(request, "Not an admin for this unit")

    # build a set of all instructors that don't have an instructor-appropriate role
    roles = dict(((r.person, r.role) for r in Role.objects.filter(unit=unit, role__in=INSTR_ROLES).select_related('person')))
    missing = set()
    long_ago = datetime.date.today() - datetime.timedelta(days=365*3)
    instructors = Member.objects.filter(role="INST", offering__owner=unit,
                                        offering__semester__start__gte=long_ago) \
                                .exclude(offering__component='CAN') \
                                .exclude(person__userid=None) \
                                .select_related('person')
    for i in instructors:
        if i.person not in roles:
            missing.add(i.person)
    missing = list(missing)
    missing.sort()
    initial = [{'person': p, 'role': None} for p in missing]
    new_exp = datetime.date.today() + datetime.timedelta(days=365)

    if request.method == 'POST':
        formset = InstrRoleFormSet(request.POST, initial=initial)
        if formset.is_valid():
            count = 0
            for f in formset.forms:
                p = f.cleaned_data['person']
                r = f.cleaned_data['role']
                if r == "NONE" or p not in missing:
                    continue
                
                r = Role(person=p, role=r, unit=unit, expiry=new_exp)
                r.save()
                count += 1

                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("new role: %s as %s") % (p.userid, r),
                      related_object=r)
                l.save()
            messages.success(request, 'Set instructor roles for %i people.' % (count))
            return HttpResponseRedirect(reverse('admin:unit_admin'))
    else:
        formset = InstrRoleFormSet(initial=initial)

    context = {'formset': formset, 'unit': unit}
    return render(request, 'coredata/missing_instructors.html', context)





# AJAX/JSON for course offering selector autocomplete
def offerings_search(request):
    if 'term' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'term' query.")
    term = request.GET['term']
    response = HttpResponse(content_type='application/json')
    data = []
    query = get_query(term, ['subject', 'number', 'section', 'semester__name', 'title'])
    offerings = CourseOffering.objects.filter(query).exclude(component="CAN").select_related('semester')
    for o in offerings:
        label = o.search_label_value()
        d = {'value': o.id, 'label': label}
        data.append(d)
    json.dump(data, response, indent=1)
    return response

# AJAX/JSON for course offering selector autocomplete with slugs
def offerings_slug_search(request, semester=None):
    if 'term' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'term' query.")
    term = request.GET['term']
    response = HttpResponse(content_type='application/json')
    data = []
    query = get_query(term, ['subject', 'number', 'section', 'semester__name', 'title'])
    offerings = CourseOffering.objects.filter(query).exclude(component="CAN").select_related('semester')
    if semester:
        offerings = offerings.filter(semester__name=semester)
    for o in offerings:
        label = o.search_label_value()
        d = {'value': o.slug, 'label': label}
        data.append(d)
    json.dump(data, response, indent=1)
    return response

# AJAX/JSON for course selector autocomplete
def course_search(request):
    if 'term' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'term' query.")
    term = request.GET['term']
    response = HttpResponse(content_type='application/json')
    data = []
    query = get_query(term, ['subject', 'number', 'title'])
    courses = Course.objects.filter(query)
    for c in courses:
        label = "%s %s" % (c.subject, c.number)
        d = {'value': c.id, 'label': label}
        data.append(d)
    json.dump(data, response, indent=1)
    return response

# AJAX/JSON for student search autocomplete
EXCLUDE_EMPLIDS = set(['953022983']) # exclude these from autocomplete
  # 953022983 is an inactive staff account and should not be assigned things


@login_required
def student_search(request):
    # check permissions
    roles = Role.all_roles(request.user.username)
    allowed = set(['ADVS', 'ADMN', 'GRAD', 'FUND', 'SYSA', 'FACA', 'FDRE'])
    if not(roles & allowed) and not has_formgroup(request) and not has_global_role('DISC', request):
        # doesn't have any allowed roles
        return ForbiddenResponse(request, "Not permitted to do student search.")
    
    if 'term' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'term' query.")
    term = request.GET['term']
    response = HttpResponse(content_type='application/json')

    # do the query with Haystack
    # experimentally, score >= 1 seems to correspond to useful things
    student_qs = SearchQuerySet().models(Person).filter(text_fuzzy=term)[:20]
    data = [{'value': r.emplid, 'label': r.search_display} for r in student_qs
            if r and r.score >= 1 and str(r.emplid) not in EXCLUDE_EMPLIDS]
    
    # non-haystack version of the above query
    if len(student_qs) == 0:
        studentQuery = get_query(term, ['userid', 'emplid', 'first_name', 'last_name'])
        students = Person.objects.filter(studentQuery)[:20]
        data = [{'value': s.emplid, 'label': s.search_label_value()} for s in students if str(s.emplid) not in EXCLUDE_EMPLIDS]

    if 'nonstudent' in request.GET and 'ADVS' in roles:
        nonStudentQuery = get_query(term, ['first_name', 'last_name', 'pref_first_name'])
        nonStudents = NonStudent.objects.filter(nonStudentQuery)[:10]
        data.extend([{'value': n.slug, 'label': n.search_label_value()} for n in nonStudents])

    #data.sort(key = lambda x: x['label'])

    json.dump(data, response, indent=1)
    return response

def offering_by_id(request):
    if 'id' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'id' query.")
    id_ = request.GET['id']
    try:
        int(id_)
    except ValueError:
        return ForbiddenResponse(request, "'id' must be an integer.")

    offering = get_object_or_404(CourseOffering, pk=id_)
    return HttpResponse(offering.search_label_value())


from coredata.queries import find_person
@login_required
def XXX_sims_person_search(request):
    # check permissions
    roles = Role.all_roles(request.user.username)
    allowed = set(['ADVS', 'ADMN', 'GRAD', 'FUND'])
    if not(roles & allowed):
        # doesn't have any allowed roles
        return ForbiddenResponse(request, "Not permitted to do person search.")
    
    if 'emplid' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'emplid' query.")
    emplid = request.GET['emplid']
    response = HttpResponse(content_type='application/json')

    data = find_person(emplid)
    
    json.dump(data, response, indent=1)
    return response


def browse_courses(request):
    """
    Interactive CourseOffering browser
    """
    if 'tabledata' in request.GET:
        # table data
        return _offering_data(request)
    if 'instructor_autocomplete' in request.GET:
        # instructor autocomplete search
        return _instructor_autocomplete(request)

    # actually displaying the page at this point
    form = OfferingFilterForm()
    context = {
        'form': form,
        }
    return render(request, 'coredata/browse_courses.html', context)




from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q, F
from django.conf import settings
import operator
import pytz
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from courselib.auth import NotFoundResponse
from coredata.models import CAMPUSES_SHORT
from coredata.forms import OfferingFilterForm, FLAG_DICT
from coredata.queries import more_offering_info, outlines_data_json, SIMSProblem
from dashboard.views import _offerings_calendar_data

COLUMNS = ['semester', 'coursecode', 'title', 'enrol', 'instructors', 'campus']
COLUMN_ORDERING = { # column -> ordering info for datatable_view
    'semester': 'semester__name',
    'coursecode': ['subject', 'number', 'section'],
    'title': 'title',
    'instructors': [],
    'enrol': 'enrl_tot',
    'campus': 'campus',
    }

class OfferingDataJson(BaseDatatableView):
    model = CourseOffering
    max_display_length = 500
    columns = COLUMNS
    order_columns = [COLUMN_ORDERING[col] for col in columns]

    def get_context_data(self, *args, **kwargs):
        try:
            return super().get_context_data(*args, **kwargs)
        except:
            raise Http404()

    def render_column(self, offering, column):
        if column == 'coursecode':
            txt = '%s\u00a0%s\u00a0%s' % (offering.subject, offering.number, offering.section) # those are nbsps
            url = reverse('browse:browse_courses_info', kwargs={'course_slug': offering.slug})
            col = mark_safe('<a href="%s">%s</a>' % (url, conditional_escape(txt)))
        elif column == 'instructors':
            col = offering.instructors_printing_str()
        elif column == 'campus':
            col = CAMPUSES_SHORT[offering.campus]
        elif column == 'enrol':
            col = '%i/%i' % (offering.enrl_tot, offering.enrl_cap)
            if offering.wait_tot:
                col += ' (+%i)' % (offering.wait_tot,)
        elif column == 'semester':
            col = str(offering.semester).replace(' ', '\u00a0') # nbsp
        elif hasattr(offering, 'get_%s_display' % column):
            # it's a choice field
            col = getattr(offering, 'get_%s_display' % column)()
        else:
            col = str(getattr(offering, column))
        
        return conditional_escape(col)

    def ordering(self, qs):
        return super(OfferingDataJson, self).ordering(qs)

    def filter_queryset(self, qs):
        # use request parameters to filter queryset
        GET = self.request.GET

        # no cancelled courses
        qs = qs.exclude(component='CAN')
        # no courses outside the allowed semester range
        qs = qs.filter(semester__in=OfferingFilterForm.allowed_semesters())
        # no locally-merged courses
        qs = qs.exclude(flags=CourseOffering.flags.combined)
        
        srch = GET.get('search[value]', None)
        if srch:
            # non-haystack version:
            #qs = qs.filter(Q(title__icontains=srch) | Q(number__icontains=srch) | Q(subject__icontains=srch) | Q(section__icontains=srch))

            # get offering set from haystack, and use it to limit our query
            offering_qs = SearchQuerySet().models(CourseOffering).filter(text__fuzzy=srch)[:500]
            offering_pks = (r.pk for r in offering_qs if r is not None)
            qs = qs.filter(pk__in=offering_pks)

        subject = GET.get('subject[]', None)
        if subject:
            qs = qs.filter(subject=subject)

        number = GET.get('number[]', None)
        if number:
            qs = qs.filter(number__istartswith=number)
            
        section = GET.get('section[]', None)
        if section:
            qs = qs.filter(section__istartswith=section)

        instructor = GET.get('instructor[]', None)
        if instructor:
            off_ids = Member.objects.order_by().filter(person__userid=instructor, role='INST').values_list('offering', flat=True)[:500]
            #qs = qs.filter(id__in=off_ids)
            # above should work, but production mySQL is ancient and can't do IN + LIMIT
            if off_ids:
                fake_in = reduce(operator.__or__, (Q(id=oid) for oid in off_ids))
                qs = qs.filter(fake_in)
            else:
                qs = qs.none()
            
        campus = GET.get('campus[]', None)
        if campus:
            qs = qs.filter(campus=campus)

        semester = GET.get('semester[]', None)
        if semester:
            qs = qs.filter(semester__name=semester)

        title = GET.get('crstitle[]', None)
        if title:
            # non-haystack version:
            #qs = qs.filter(title__icontains=title)

            # get offering set from haystack, and use it to limit our query
            offering_qs = SearchQuerySet().models(CourseOffering).filter(title__fuzzy=title)[:500]
            offering_pks = (r.pk for r in offering_qs if r is not None)
            qs = qs.filter(pk__in=offering_pks)

        wqb = GET.getlist('wqb[]')
        for f in wqb:
            if f not in FLAG_DICT:
                continue # not in our list of flags: not safe to getattr
            qs = qs.filter(flags=getattr(CourseOffering.flags, f))

        mode = GET.get('mode[]', None)
        if mode == 'dist':
            qs = qs.filter(instr_mode='DE')
        elif mode == 'on':
            qs = qs.exclude(instr_mode='DE')
        elif mode == 'day':
            qs = qs.exclude(instr_mode='DE').exclude(section__startswith='E')
        elif mode == 'eve':
            qs = qs.exclude(instr_mode='DE').filter(section__startswith='E')

        # free space filter
        space_filters = GET.getlist('space[]')
        if 'seats' in space_filters:
            qs = qs.filter(enrl_tot__lt=F('enrl_cap'))
        if 'nowait' in space_filters:
            qs = qs.filter(wait_tot=0)

        return qs

    #def XXX_prepare_results(self, qs):
    #    "Prepare for mData-style data handling"
    #    data = []
    #    for item in qs:
    #        data.append(dict((column, self.render_column(item, column)) for column in self.get_columns()))
    #    return data

    #def get_context_data(self, *args, **kwargs):
    #    data = super(OfferingDataJson, self).get_context_data(*args, **kwargs)
    #    data['colinfo'] = [(c, COLUMN_NAMES.get(c, '???')) for c in self.get_columns()]
    #    return data

_offering_data = OfferingDataJson.as_view()


def _instructor_autocomplete(request):
    """
    Responses for the jQuery autocomplete for instructor search: key by userid not emplid for privacy
    """
    if 'term' not in request.GET:
        return ForbiddenResponse(request, "Must provide 'term' query.")

    response = HttpResponse(content_type='application/json')

    """ # non-haystack version
    query = get_query(request.GET['term'], ['person__first_name', 'person__last_name', 'person__userid', 'person__middle_name'])
    # matching person.id values who have actually taught a course
    person_ids = Member.objects.filter(query).filter(role='INST') \
                 .exclude(person__userid=None).order_by() \
                 .values_list('person', flat=True).distinct()[:500]
    person_ids = list(person_ids) # shouldn't be necessary, but production mySQL can't do IN + LIMIT
    # get the Person objects: is there no way to do this in one query?
    people = Person.objects.filter(id__in=person_ids)
    """

    term = request.GET['term']
    # strip any digits from the query, so users can't probe emplids with the search (emplid is the only digit-containing
    # thing in the Person text index)
    term = ''.join(c for c in term if not c.isdigit())
    # query with haystack
    person_qs = SearchQuerySet().models(Person).filter(text__fuzzy=term)[:100]
    person_pks = (r.pk for r in person_qs if r is not None)
    # go back to the database to limit to only instructors
    instr_ids = Member.objects.filter(person_id__in=person_pks).filter(role='INST') \
                 .exclude(person__userid=None).order_by() \
                 .values_list('person', flat=True).distinct()[:20]
    instr_ids = list(instr_ids) # shouldn't be necessary, but production mySQL can't do IN + LIMIT
    people = Person.objects.filter(id__in=instr_ids)

    data = [{'value': p.userid, 'label': p.name()} for p in people]
    json.dump(data, response, indent=1)
    return response


def browse_courses_info(request, course_slug):
    """
    Browsing info about a single course offering.
    """
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    if offering.flags.combined:
        return NotFoundResponse(request)

    if 'data' in request.GET:
        # more_course_info data requested
        response = HttpResponse(content_type='application/json')
        try:
            data = more_offering_info(offering, browse_data=True, offering_effdt=True)
        except SIMSProblem as e:
            data = {'error': str(e)}
        json.dump(data, response, indent=1)
        return response

    elif 'caldata' in request.GET:
        # calendar data requested
        return _offering_meeting_time_data(request, offering)

    elif 'outline' in request.GET:
        # course outline data requested
        response = HttpResponse(content_type='application/json')
        data = outlines_data_json(offering)
        response.write(data)
        return response

    # the page itself (with most data assembled by AJAX requests to the above)
    context = {
        'offering': offering,
    }
    return render(request, 'coredata/browse_courses_info.html', context)


def _offering_meeting_time_data(request, offering):
    """
    fullcalendar.js data for this offering's events
    """
    try:
        st = iso8601.parse_date(request.GET['start'])
        en = iso8601.parse_date(request.GET['end'])
    except (KeyError, ValueError, iso8601.ParseError):
        return NotFoundResponse(request, errormsg="Bad request")

    local_tz = pytz.timezone(settings.TIME_ZONE)
    start = st - datetime.timedelta(days=1)
    end = en + datetime.timedelta(days=1)

    response = HttpResponse(content_type='application/json')
    data = list(_offerings_calendar_data([offering], None, start, end, local_tz,
                                         dt_string=True, colour=True, browse_titles=True))
    json.dump(data, response, indent=1)
    return response


@requires_role("ADMN")
def new_temporary_person(request):
    if request.method == 'POST':
        form = TemporaryPersonForm(request.POST)
        if form.is_valid():
            p = Person( first_name = form.cleaned_data['first_name'], 
                        last_name = form.cleaned_data['last_name'],
                        emplid = Person.next_available_temp_emplid(),
                        userid = Person.next_available_temp_userid(), 
                        temporary = True)
            if form.cleaned_data['email']:
                p.config['email'] = form.cleaned_data['email']
            if form.cleaned_data['sin']:
                p.config['sin'] = form.cleaned_data['sin']

            p.save()

            messages.success(request, 'Added new temporary person %s' % (p,))
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new temporary person: %s") % (p,),
                  related_object=p)
            l.save()
            return HttpResponseRedirect(reverse('admin:unit_admin'))
    else:
        form = TemporaryPersonForm()

    return render(request, 'coredata/new_temporary_person.html', {'form': form})


@cached(3600*12)
def _has_homepages(unit_id, semester_id):
    offerings = CourseOffering.objects.filter(owner_id=unit_id, semester_id=semester_id, graded=True) \
        .exclude(component='CAN') \
        .exclude(instr_mode__in=['CO', 'GI']) \
        .filter(config__contains='"url"')
    offerings = [o for o in offerings if 'url' in o.config]
    return bool(offerings)

def course_home_pages(request):
    semester = Semester.current()
    units = Unit.objects.all().order_by('label')
    units = [u for u in units if _has_homepages(u.id, semester.id)]
    context = {
        'semester': semester,
        'units': units,
    }
    return render(request, "coredata/course_home_pages.html", context)

def course_home_pages_unit(request, unit_slug, semester=None):
    if semester:
        semester = get_object_or_404(Semester, name=semester)
    else:
        semester = Semester.current()

    unit = get_object_or_404(Unit, slug=unit_slug)
    offerings = CourseOffering.objects.filter(semester=semester, owner=unit, graded=True) \
        .exclude(component='CAN') \
        .exclude(instr_mode__in=['CO', 'GI'])

    if request.user.is_authenticated:
        is_admin = Role.objects_fresh.filter(unit=unit, person__userid=request.user.username, role='ADMN').exists()
    else:
        is_admin = False

    context = {
        'semester': semester,
        'unit': unit,
        'offerings': offerings,
        'is_admin': is_admin,
    }
    return render(request, "coredata/course_home_pages_unit.html", context)

@requires_role('ADMN')
def course_home_admin(request, course_slug):
    offering = get_object_or_404(CourseOffering, slug=course_slug, owner__in=request.units)
    if request.method == 'POST':
        form = CourseHomePageForm(data=request.POST)
        if form.is_valid():
            offering.set_url(form.cleaned_data['url'])
            if 'maillist' in form.cleaned_data and form.cleaned_data['maillist']:
                offering.set_maillist(form.cleaned_data['maillist'])

            offering.save()

            messages.success(request, 'Updated URL for %s.' % (offering.name()))
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("Updated course URL for %s.") % (offering.name()),
                  related_object=offering)
            l.save()
            return HttpResponseRedirect(reverse('browse:course_home_pages_unit', kwargs={'unit_slug': offering.owner.slug, 'semester': offering.semester.name}))

    else:
        form = CourseHomePageForm(initial={'url': offering.url(), 'maillist': offering.maillist()})

    context = {
        'offering': offering,
        'form': form,
    }
    return render(request, "coredata/course_home_admin.html", context)
