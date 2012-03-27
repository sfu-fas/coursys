from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.contrib import messages
from courselib.auth import requires_course_staff_by_slug, requires_course_instr_by_slug, requires_role, \
    is_course_staff_by_slug, requires_course_staff_or_dept_admn_by_slug, \
    has_role, ForbiddenResponse
from django.contrib.auth.decorators import login_required
from ta.models import TUG, Skill, SkillLevel, TAApplication, TAPosting, TAContract, TACourse, CoursePreference, CampusPreference,\
    CAMPUS_CHOICES, CAMPUSES, PREFERENCE_CHOICES, LEVEL_CHOICES, PREFERENCES, LEVELS
from ra.models import Account
from dashboard.models import NewsItem
from coredata.models import Member, Role, CourseOffering, Person, Semester
from grad.models import GradStatus
from ta.forms import TUGForm, TAApplicationForm, TAContractForm, TAAcceptanceForm, CoursePreferenceForm, \
    TAPostingForm, TAPostingBUForm, BUFormSet, TACourseForm, BaseTACourseFormSet, AssignBUForm
from advisornotes.forms import StudentSearchForm
from log.models import LogEntry
from dashboard.letters import ta_form, ta_forms
from django.forms.models import inlineformset_factory
from django.forms.formsets import formset_factory
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.servers.basehttp import FileWrapper
import os
import datetime, decimal, locale 
import unicodecsv as csv
from ta.templatetags import ta_display
import json

locale.setlocale( locale.LC_ALL, '' ) #fiddle with this if you cant get the following function to work
def format_currency(i):
    """used to properly format money"""
    return locale.currency(float(i), grouping=True)

def get_total_bu(courses):
    """calculates the total bu given a list of courses"""
    total = 0
    for course in courses:
        total = total + course.bu
    return total

def create_news(person, url, from_user):
    n = NewsItem(user=person, source_app="ta_contract", title="TA Contract Offer for %s" % (person),
                 url=url, author=from_user)
    n.save()

@login_required
def index_page(request, course_slug):
    return HttpResponseRedirect(reverse(all_tugs, args=(course_slug,)))

# helps zip tas and tugs together
# basically performs a left outer join between tas and tugs
def tryget(member):
    try:
        return TUG.objects.get(member=member)
    except(TUG.DoesNotExist):
        return None
    
@requires_course_staff_by_slug
def all_tugs(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    tas = Member.objects.filter(offering=course, role="TA")
    current_user = Member.objects.get(person__userid=request.user.username, offering=course)
    #If a TA is accessing, only his/her own TUG should be viewable
#    is_ta = current_user in tas
    is_ta = current_user.role == 'TA'
    if is_ta:
        # TODO: just redirect if the user is just a TA (ask in scrumeeting)
        tas = [current_user]
        #tas = tas.filter(person__userid=current_user.person.userid)
    tas_with_tugs = [(ta, tryget(ta)) for ta in tas]
    
    context = {
           'tas_with_tugs':tas_with_tugs,
           'course':course,
           'not_ta':not is_ta
            }
    
    return render(request, 'ta/all_tugs.html', context)
        
@requires_role("ADMN")
def all_tugs_admin(request):
    unit = Role.objects.get(person__userid=request.user.username).unit
    courses = CourseOffering.objects.filter(owner=unit) # TO DO: Make this reference the CourseOffering's "Owner" field once it's been added
    tas = Member.objects.filter(offering__in=courses, role="TA")
    tas_with_tugs = [{'ta':ta, 'tug':tryget(ta)} for ta in tas]
    
    context = {
               'tas_with_tugs':tas_with_tugs,
               'unit':unit,
               'courses':courses,
               # todo: figure out a way to express empty_courses in template code
               # perhaps write a custom filter
               'empty_courses':[course for course in courses if not any(course == ta.offering for ta in tas )]
                }
    
    return render(request, 'ta/all_tugs_admin.html', context)


@requires_course_instr_by_slug    
def new_tug(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=userid)
#    curr_user_role = Member.objects.get(person__userid=request.user.username,offering=course).role
    
    # TAs should not be creating TUGs
#    if(curr_user_role =="TA" and not userid==request.user.username ): 
#        return ForbiddenResponse(request)
#    else:
    # Nothing is done as of now until further details as to how to "pre-fill" 
    # #158    TUG: courses with lab sections should be pre-filled as appropriate
    has_lab_or_tut = course.labtut()# placeholder until the following line works
    #TODO: add 'labta' config field to member
    #has_lab_or_tut = course.labtas() and member.labta()
        
    if request.method == "POST":
        form = TUGForm(data=request.POST, offering=course,userid=userid)
        if form.is_valid():
            tug = form.save(False)
            tug.save(newsitem_author=Person.objects.get(userid=request.user.username))
            return HttpResponseRedirect(reverse(view_tug, args=(course.slug, userid)))
    else:
        if has_lab_or_tut:
            form = TUGForm(offering=course,userid=userid, initial=
                    {'other1':{'label':'Planning','total':13,
                               'comment':'Attendance at a TA/TM Day/Training'}})
        else:
            form = TUGForm(offering=course,userid=userid)
    
    context = {'ta':member.person,
               'course':course,
               'form':form,
               'userid':userid,
               #'hasLabOrTut': has_lab_or_tut
               }
    return render(request,'ta/new_tug.html',context)

@requires_course_staff_or_dept_admn_by_slug    
def view_tug(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=userid, role="TA")
    try:
        curr_user_role = Member.objects.get(person__userid=request.user.username,offering=course).role
    except Member.DoesNotExist:
        # we'll just assume this since it's the only other possibility 
        #  since we're checking authorization in the decorator
        curr_user_role = "ADMN"
    
    #If the currently logged in user is a TA for the course and is viewing a TUG for another TA, show forbidden message
    if(curr_user_role =="TA" and not userid==request.user.username ): 
        return ForbiddenResponse(request)
    else:
        tug = get_object_or_404(TUG, member=member)
        max_hours = tug.base_units * 42
        total_hours = sum(decimal.Decimal(params.get('total',0)) for _, params in tug.config.iteritems() if params.get('total',0) is not None)
        
        context = {'tug': tug, 'ta':member, 'course':course, 
                'maxHours':max_hours, 'totalHours':total_hours,
                'user_role':curr_user_role}
        return render(request, 'ta/view_tug.html',context)

@requires_course_instr_by_slug
def edit_tug(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=userid)
    tug = get_object_or_404(TUG,member=member)
    if (request.method=="POST"):
        form = TUGForm(request.POST, instance=tug)
        if form.is_valid():
            tug = form.save(False)
            tug.save(newsitem_author=Person.objects.get(userid=request.user.username))
            return HttpResponseRedirect(reverse(view_tug, args=(course.slug, userid)))
    else:
        form = TUGForm(instance=tug)
    context = {'ta':member.person,
               'course':course, 
               'form': form, 
               'userid':userid,
               #'tug':tug 
               }
    
    return render(request, 'ta/edit_tug.html',context)

@requires_role("TAAD")
def new_application_manual(request, post_slug):
    return _new_application(request, post_slug, manual=True)

@login_required
def new_application(request, post_slug):
    return _new_application(request, post_slug, manual=False)

def _new_application(request, post_slug, manual=False):
    posting = get_object_or_404(TAPosting, slug=post_slug)
    course_choices = [(c.id, unicode(c)) for c in posting.selectable_courses()]
    used_campuses = set((vals['campus'] for vals in posting.selectable_offerings().order_by('campus').values('campus').distinct()))
    skills = Skill.objects.filter(posting=posting)
    
    #Set default values for max and min courses if not in posting config
    try:
        max_courses = posting.config['max_courses']
    except KeyError:
        max_courses = 10;
    try:
        min_courses = posting.config['min_courses']
    except KeyError:
        min_courses = 1;

    CoursesFormSet = formset_factory(CoursePreferenceForm, extra=min_courses, max_num=max_courses) 
 
    if not manual: 
        person = get_object_or_404(Person, userid=request.user.username)
        existing_app = TAApplication.objects.filter(person=person, posting=posting)
        if existing_app.count() > 0: 
            messages.success(request, "You have already applied for the %s %s posting." % (posting.unit, posting.semester))
            return HttpResponseRedirect(reverse('ta.views.view_application', kwargs={'post_slug': existing_app[0].posting.slug, 'userid': existing_app[0].person.userid}))
       
    if request.method == "POST":
        search_form = StudentSearchForm(request.POST)
        #Try to manually retrieve person
        if manual:
            try:
                person = get_object_or_404(Person, emplid=int(request.POST['search']))
            except ValueError:
                search_form = StudentSearchForm(request.POST['search'])
                messages.error(request, "Invalid id %s for person." % (request.POST['search']))
                if manual:
                    return HttpResponseRedirect(reverse('ta.views.new_application_manual', args=(post_slug,)))
                else:
                    return HttpResponseRedirect(reverse('ta.views.new_application', args=(post_slug,)))
        ta_form = TAApplicationForm(request.POST, prefix='ta')
        courses_formset = CoursesFormSet(request.POST)
        for f in courses_formset:
            f.fields['course'].choices = course_choices

        if ta_form.is_valid() and courses_formset.is_valid():
            app = ta_form.save(commit=False)
            today = datetime.date.today()
            if(posting.closes < today):
                app.late = True
            else:
                app.late = False
            app.posting = posting
            app.person = person
            app.save()
            ta_form.save_m2m()
            
            # extract campus and skill values; create objects
            for c in used_campuses:
                val = request.POST.get('campus-'+c, None)
                if val not in PREFERENCES:
                    val = 'WIL'
                cp = CampusPreference(app=app, campus=c, pref=val)
                cp.save()
            
            for s in skills:
                val = request.POST.get('skill-'+str(s.position), None)
                if val not in LEVELS:
                    val = 'NONE'
                sl = SkillLevel(skill=s, app=app, level=val)
                sl.save()
            
            # save course preferences
            for (rank,form) in enumerate(courses_formset):
                course = form.save(commit=False)
                course.app = app
                course.rank = rank+1
                course.save()
            return HttpResponseRedirect(reverse('ta.views.view_application', kwargs={'post_slug': app.posting.slug, 'userid': app.person.userid}))
        
        # redisplaying form: build values for template with entered values
        campus_preferences = []
        for c in used_campuses:
            val = request.POST.get('campus-'+c, None)
            if val not in PREFERENCES:
                val = 'WIL'
            campus_preferences.append((c, CAMPUSES[c], val))
        skill_values = []
        for s in skills:
            val = request.POST.get('skill-'+str(s.position), None)
            if val not in LEVELS:
                val = 'NONE'
            skill_values.append((s.position, s.name, val))

    elif request.is_ajax():
        # TO DO: Update formset to correct number of forms displayed
        return HttpResponse("AJAX Completed") #return updated form.
    else:
        search_form = StudentSearchForm()
        courses_formset = CoursesFormSet()
        for f in courses_formset:
            f.fields['course'].choices = course_choices
        ta_form = TAApplicationForm(prefix='ta')
        campus_preferences = [(lbl, name, 'WIL') for lbl,name in CAMPUS_CHOICES if lbl in used_campuses]
        skill_values = [(s.position, s.name, 'NONE') for s in skills]
        today = datetime.date.today()
        if(posting.closes < today):
            messages.warning(request, "The closing date for this posting has past.  Your application will be marked 'late' and may not be considered.")
    context = {
                    'posting':posting,
                    'manual':manual,
                    'ta_form':ta_form,
                    'search_form':search_form,
                    'courses_formset':courses_formset,
                    'campus_preferences':campus_preferences,
                    'campus_pref_choices':PREFERENCE_CHOICES,
                    'skill_values': skill_values,
                    'skill_choices': LEVEL_CHOICES,
                  }
    return render(request, 'ta/new_application.html', context)

@requires_role("TAAD")
def update_application(request, post_slug, userid):
    application = get_object_or_404(TAApplication, posting__slug=post_slug, person__userid=userid, posting__unit__in=request.units)
    application.late = False
    application.save()
    messages.success(request, "Removed late status from the application.")
    return HttpResponseRedirect(reverse(view_application, kwargs={'post_slug': application.posting.slug, 'userid': application.person.userid}))
    

@login_required
def view_application(request, post_slug, userid):
    application = get_object_or_404(TAApplication, posting__slug=post_slug, person__userid=userid)
    roles = Role.objects.filter(role="TAAD", person__userid=request.user.username)
   
    #Only TA Administrator or owner of application can view it
    if application.person.userid != request.user.username:
        units = [r.unit for r in roles]
        if roles.count() == 0:
            return ForbiddenResponse(request, 'You cannot access this application')
        elif application.posting.unit not in units:
            return ForbiddenResponse(request, 'You cannot access this application')
   
    courses = CoursePreference.objects.filter(app=application)
    skills = SkillLevel.objects.filter(app=application).select_related('skill')
    campuses = CampusPreference.objects.filter(app=application).select_related('campus')
    context = {
            'application':application,
            'courses':courses,
            'skills': skills,
            'campuses': campuses,
            }
    return render(request, 'ta/view_application.html', context)

@requires_role("TAAD")
def view_late_applications(request,post_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug, unit__in=request.units)
    applications = TAApplication.objects.filter(posting__slug=post_slug, late=True)
    context = {
        'posting': posting,
        'applications':applications,
    }
    return render(request, 'ta/late_applications.html', context)

@login_required
def view_postings(request):
    roles = Role.objects.filter(role="TAAD", person__userid=request.user.username)
    units = [r.unit for r in roles]
    today = datetime.date.today()
    postings = TAPosting.objects.filter(opens__lte=today, closes__gte=today).order_by('-semester', 'unit')
    owned = TAPosting.objects.filter(unit__in=units).order_by('-semester', 'unit')
    context = {
            'postings': postings,
            'owned': owned,
            'is_admin': bool(roles),
            }
    return render(request, 'ta/view_postings.html', context) 

@requires_role("TAAD")
def assign_tas(request, post_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this page')
    
    all_offerings = CourseOffering.objects.filter(semester=posting.semester, owner=posting.unit)
    # ignore excluded courses
    excl = set(posting.excluded())
    offerings = [o for o in all_offerings if o.course_id not in excl]
    excluded = [o for o in all_offerings if o.course_id in excl]
    
    context = {'posting': posting, 'offerings': offerings, 'excluded': excluded}
    return render(request, 'ta/assign_tas.html', context) 

@requires_role("TAAD")
def assign_bus(request, post_slug, course_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this page')
    
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    instructors = offering.instructors()
    course_prefs = CoursePreference.objects.filter(course=offering.course,app__late=False) 
    #a ta that has been assigned BU to this course might not be on the list
    tacourses = TACourse.objects.filter(course=offering)
    
    if request.method == "POST" and request.is_ajax():
        act = 0
        extra = 0
        msg = ''
        req_bu = ''
        rem_bu = ''
        
        extra_bu = request.POST['extra_bu']
        if extra_bu != '':
            try:
                extra_bu = decimal.Decimal(extra_bu)
                if extra_bu != offering.extra_bu():
                    offering.config['extra_bu'] = extra_bu
                    req_bu = ta_display.display_bu(offering, posting)
                    rem_bu = ta_display.display_bu_difference(offering, posting)
            except:
                msg = "Extra BU needs to be a decimal number."
         
        if request.POST['labtas'] == "yes":
            if not offering.labtas(): #changed from F to T
                offering.config['labtas'] = True
                act = 1
        else:
            if offering.labtas(): #changed from T to F
                offering.config['labtas'] = False
                act = -1
        offering.save()
        data = {'act': act , 'msg': msg, 'req_bu': req_bu, 'rem_bu': rem_bu }
        return HttpResponse(json.dumps( data ))

    apps = []
    campus_prefs = []
    assigned_ta = []
    initial = []
    
    for p in course_prefs:
        init = {}
        assigned = None
        statuses = GradStatus.objects.filter(student__person=p.app.person, end=None).select_related('student__program__unit')
        p.app.statuses = statuses # annotate the application with their current grad status(es)
        apps.append(p.app)
        try:
            campus_preference = CampusPreference.objects.get(app=p.app, campus=offering.campus)
        except CampusPreference.DoesNotExist:
            # temporary fake object: shouldn't happen, but don't die if it does
            campus_preference = CampusPreference(app=p.app, campus=offering.campus, pref="NOT")
        campus_prefs.append(campus_preference)
        #find BU assigned to this applicant through contract
        app_tacourse = tacourses.filter(contract__application=p.app)
        if app_tacourse.count() == 1:
            init['bu'] = app_tacourse[0].bu
            assigned = app_tacourse[0]
        assigned_ta.append(assigned)
        init['rank'] = p.app.rank
        initial.append(init)

    AssignBUFormSet = formset_factory(AssignBUForm)
    
    #Save ranks and BU's
    if request.method == "POST":
        formset = AssignBUFormSet(request.POST)
        if formset.is_valid():
            for i in range(len(apps)):
                #update rank
                apps[i].rank = formset[i]['rank'].value()
                apps[i].save()
                
                if assigned_ta[i] == None: 
                    #create new TACourse if bu field is nonempty
                    if formset[i]['bu'].value() != '':
                        #create new TAContract if there isn't one
                        contracts = TAContract.objects.filter(application=apps[i], posting=posting)
                        if contracts.count() > 0: #count is 1
                            contract = contracts[0]
                        else:
                            contract = TAContract(created_by=request.user.username)
                            contract.first_assign(apps[i], posting)
                        bu = formset[i]['bu'].value()
                        tacourse = TACourse.objects.create(course=offering, description=offering.get_desc(), contract=contract, bu=bu)
                else: 
                    #update bu for existing TACourse
                    if formset[i]['bu'].value() != '':
                        assigned_ta[i].bu = formset[i]['bu'].value()
                        assigned_ta[i].save()                        
                    #unassign bu to this offering for this applicant
                    else:
                        assigned_ta[i].delete()
            return HttpResponseRedirect(reverse(assign_tas, args=(post_slug,)))
    else:
        formset = AssignBUFormSet(initial=initial)
    
    #add class to bu input for js
    """
    for i in range(len(apps)):
        formset[i].fields['bu'].widget.attrs['class']  = 'bu_inp'
        if assigned_ta[i] != None and assigned_ta[i].description == 'OML':
            formset[i].fields['bu'].help_text = 'TA runs lab'
    """
    
    context = {'formset':formset, 'posting':posting, 'offering':offering, 'instructors':instructors, 'applications': apps, 'course_preferences': course_prefs, 'campus_preferences':campus_prefs}
    return render(request, 'ta/assign_bu.html', context) 

@requires_role("TAAD")
def all_contracts(request, post_slug):    
    #name, appointment category, rank, deadline, status. Total BU, Courses TA-ing , view/edit
    posting = get_object_or_404(TAPosting, slug=post_slug, unit__in=request.units)
    contracts = TAContract.objects.filter(posting=posting)
    paginator = Paginator(contracts,5)
    
    try:
        p = int(request.GET.get("page",'1'))
    except ValueError:p=1
    
    try:
        contract_page = paginator.page(p)
    except(InvalidPage, EmptyPage):
        contract_page.paginator.page(paginator.num_pages)
    
    if request.method == "POST":
        ccount = 0
        for contract in contracts:
            cname = u'contract_%s' % contract.id
            if cname in request.POST:
                #send offer for this offer
                #update status to offerred (pre validation?)
                contract.status = 'OPN'
                contract.save()
                ccount += 1
        if ccount > 1:
            messages.success(request, "Successfully sent %s offers." % ccount)
        elif ccount > 0:
            messages.success(request, "Successfully sent offer")
            
    for contract in contracts:
        total_bu =0
        crs_list = ''
        courses = TACourse.objects.filter(contract=contract)
        for course in courses:
            total_bu += course.bu
            crs_list += course.course.subject+" "+course.course.number+" "+course.course.section+"("+str(course.bu)+")\n"
        contract.total_bu = total_bu
        contract.crs_list = crs_list    
            
    #postings = TAPosting.objects.filter(unit__in=request.units).exclude(Q(semester=posting.semester))
    applications = TAApplication.objects.filter(posting=posting).exclude(Q(id__in=TAContract.objects.filter(posting=posting).values_list('application', flat=True)))
    return render(request, 'ta/all_contracts.html', {'contracts':contracts, 'posting':posting, 'applications':applications})

@requires_role("TAAD")
def contracts_csv(request, post_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug, unit__in=request.units)
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'inline; filename=%s.csv' % (posting.slug)
    writer = csv.writer(response)
    writer.writerow(['Batch ID', 'Term ID', 'Contract Signed', 'Benefits Indicator', 'EmplID', 'SIN',
                     'Last Name', 'First Name 1', 'First Name 2', 'Payroll Start Date', 'Payroll End Date',
                     'Action', 'Action Reason', 'Position Number', 'Job Code', 'Full_Part time', 'Pay Group',
                     'Employee Class', 'Category', 'Fund', 'Dept ID (cost center)', 'Project', 'Account',
                     'Prep Units', 'Base Units', 'Appt Comp Freq', 'Semester Base Salary Rate',
                     'Biweekly Base Salary Pay Rate', 'Hourly Rate', 'Standard Hours', 'Scholarship Rate Code',
                     'Semester Scholarship Salary Pay Rate', 'Biweekly Scholarship Salary Pay Rate', 'Lump Sum Amount',
                     'Lump Sum Hours', 'Scholarship Lump Sum'])
    
    contracts = TAContract.objects.filter(posting=posting, status__in=['ACC', 'SGN']) \
                .select_related('semester', 'application__person')
    batchid = '%s_%s_01' % (posting.unit.label, datetime.date.today().strftime("%Y%m%d"))
    for c in contracts:
        courses = TACourse.objects.filter(contract=c)
        total_bu = 0
        prep_units = 0
        for crs in courses:
            total_bu += crs.bu
            if crs.has_labtut():
                prep_units += 0.17
        
        signed = 'Y' if c.status=='SGN' else 'N'
        benefits = 'Y'
        schol_rate = 'TSCH' if c.scholarship_per_bu else ''
        salary_total = (total_bu + prep_units) * c.pay_per_bu
        schol_total = (total_bu + prep_units) * c.scholarship_per_bu
        row = [batchid, posting.semester.name, signed, benefits, c.application.person.emplid, c.application.sin]
        row.extend([c.application.person.last_name, c.application.person.first_name, c.application.person.middle_name])
        row.extend([c.pay_start.strftime("%Y%m%d"), c.pay_end.strftime("%Y%m%d"), 'REH', 'REH'])
        row.extend([c.position_number.position_number, '', '', 'TSU', '', c.application.category])
        row.extend(['*fund*', posting.unit.deptid(), '', c.position_number.account_number, prep_units, total_bu])
        row.extend(['T', "%.2f"%(salary_total), '', '', '', schol_rate, "%.2f"%(schol_total), '', '', '', ''])
        writer.writerow(row)
    
    return response
    


@login_required
def accept_contract(request, post_slug, userid):
    posting = get_object_or_404(TAPosting, slug=post_slug)
    person = get_object_or_404(Person, userid=request.user.username)
    
    contract = TAContract.objects.filter(posting=posting, application__person__userid=userid)
    if contract.count() > 0:
        contract = contract[0]
        application = TAApplication.objects.get(person__userid=userid, posting=posting)
        
    courses = TACourse.objects.filter(contract=contract)
    total = get_total_bu(courses)
    
    if request.method == "POST":
        form = TAAcceptanceForm(request.POST, instance=contract)
        print
        print form.fields
        print form.is_valid()
        print form.errors
        if form.is_valid():
            contract =form.save(commit=False)
            contract.posting = posting
            contract.application = application
            contract.sin = request.POST['sin']
            contract.status = request.POST['status']
            contract.save()
            messages.success(request, "Successfully %s the offer." % (contract.get_status_display()))
            ##not sure where to redirect to...so currently redirects to itself
            return HttpResponseRedirect(reverse(accept_contract, args=(post_slug,userid)))
    else:   
        form = TAContractForm(instance=contract) 
        
    
    context = {'contract':contract, 
               'person': person,
               'courses':courses,
               'total':total,
               'form':form}
    return render(request, 'ta/accept.html', context)

@requires_role("TAAD")
def view_contract(request, post_slug, userid):
    #contract = get_object_or_404(TAContract, pk=contract_id)
    #ta courses get all courses with contract_id
    #courses = TACourse.objects.filter(contract=contract)
    #contract.pay_per_bu = format_currency(contract.pay_per_bu)
    #contract.scholarship_per_bu = format_currency(contract.scholarship_per_bu)
    
    posting = get_object_or_404(TAPosting, slug=post_slug, unit__in=request.units)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this page')
    contract = TAContract.objects.filter(posting=posting, application__person__userid=userid)
    if contract.count() > 0:
        contract = contract[0]
    courses = TACourse.objects.filter(contract=contract)
    
    total = get_total_bu(courses)
    
    pp = posting.config['payperiods']
    salary_sem = (total*contract.pay_per_bu)
    schol_sem = (total*contract.scholarship_per_bu)
    salary_sem_out = format_currency(salary_sem)
    schol_sem_out = format_currency(schol_sem)
    salary_bi = format_currency(salary_sem / pp)
    schol_bi = format_currency(schol_sem / pp)


    context =   {'posting': posting,
                 'contract':contract,
                 'courses':courses,
                 'pay':format_currency(contract.pay_per_bu),
                 'scholarship':format_currency(contract.scholarship_per_bu),
                 'salary_bi':salary_bi,
                 'schol_bi':schol_bi,
                 'salary_sem':salary_sem_out,
                 'schol_sem':schol_sem_out,
                 'total':total
                 }
     
    
    
    return render(request, 'ta/view_contract.html', context)

@requires_role("TAAD")
def view_form(request, post_slug, userid):
    posting = get_object_or_404(TAPosting, slug=post_slug, unit__in=request.units)
    contract = get_object_or_404(TAContract, posting=posting, application__person__userid=userid)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=%s-%s.pdf' % (posting.slug, userid)
    ta_form(contract, response)
    return response

@requires_role("TAAD")
def contracts_forms(request, post_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug, unit__in=request.units)
    contracts = TAContract.objects.filter(posting=posting, status='ACC')
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=%s.pdf' % (posting.slug)
    ta_forms(contracts, response)
    return response


@requires_role("TAAD")
def edit_contract(request, post_slug, userid):
    posting = get_object_or_404(TAPosting, slug=post_slug, unit__in=request.units)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this page')
        
    course_choices = [('','---------')] + [(c.id, c.name()) for c in posting.selectable_offerings()]
    position_choices = [(a.id, "%s (%s)" % (a.position_number, a.title)) for a in Account.objects.filter(unit=posting.unit)]
    
    #number of course form to populate
    num = 3
    contract = TAContract.objects.filter(posting=posting, application__person__userid=userid)
    if contract.count() > 0:
        contract = contract[0]
        application = contract.application
        num = num - contract.tacourse_set.all().count()
        old_status = contract.get_status_display()
        if contract.status not in ['NEW', 'OPN']:
            # after editing, revert to open
            contract.status = 'OPN'
        editing = True
    else:
        # creating new contract
        contract = TAContract()
        application = TAApplication.objects.get(person__userid=userid, posting=posting)
        old_status = None
        editing = False
    
    TACourseFormset = inlineformset_factory(TAContract, TACourse, extra=num, can_delete=editing, form=TACourseForm, formset=BaseTACourseFormSet)
    formset = TACourseFormset(instance=contract)
    if request.method == "POST":
        form = TAContractForm(request.POST, instance=contract)
        
        if request.is_ajax():
            if('appt_cat' in request.POST):
                index = posting.cat_index(request.POST['appt_cat'])
                results = posting.salary()[index] + ',' + posting.scholarship()[index] + ',' + str(posting.accounts()[index])
                return HttpResponse(results)
            if('course' in request.POST):
                results = ''
                course = request.POST['course']
                co = get_object_or_404(CourseOffering, pk=course)
                req_bu = posting.required_bu(co)
                assigned_bu = posting.assigned_bu(co)
                #subtracting assigned_bu from req_bu
                if(assigned_bu > req_bu):
                    req_bu = 0.0
                else:
                    req_bu -= assigned_bu
                
                results += str(req_bu)
                if co.labtas():
                    results += ',OML'
                else:
                    results += ',OM'
                return HttpResponse(results)
        elif form.is_valid():
            contract = form.save(commit=False)
            formset = TACourseFormset(request.POST, instance=contract)
            if formset.is_valid():
                #If course isn't in applicants prefered courses, add it with rank 0
                course_prefs = [c.course for c in CoursePreference.objects.filter(app=application)]
                for form in formset:
                    if 'course' not in form.cleaned_data:
                        continue
                    offering = form.cleaned_data['course']
                    if offering.course not in course_prefs:
                        new_course_pref = CoursePreference(app=application, course=offering.course, taken='YES', exper='FAM', rank=0)
                        new_course_pref.save()

                contract.application = application
                contract.posting = posting
                contract.created_by = request.user.username
                
                #create news item
                # if contract.status == "OPN":
                person = application.person
                
                #offer_url = "http://127.0.0.1:8000/ta/contracts/"+ post_slug +"/"+ userid +"/accept"
                offer_url = reverse('ta.views.accept_contract', kwargs={'post_slug': post_slug, 'userid': userid})
                print
                print person
                print "TA Contract Offer for %s" %person
                print offer_url
                from_user = posting.contact()
                create_news(person, offer_url, from_user)
                
                contract.save()
                formset.save()

                if not editing:
                    messages.success(request, "Created TA Contract for %s for %s." % (contract.application.person, posting))
                else:
                    messages.success(request, "Edited TA Contract for %s for %s." % (contract.application.person, posting))
                return HttpResponseRedirect(reverse(all_contracts, args=(post_slug,)))
    else:
        form = TAContractForm(instance=contract) 
        formset = TACourseFormset(instance=contract)
        if not editing:
            initial={'sin': application.sin,
                     'appt_category': application.category,
                     'position_number': posting.accounts()[posting.cat_index(application.category)],
                     'pay_start': posting.start(), 
                     'pay_end': posting.end(), 
                     'deadline': posting.deadline()
                     }
                     
            form = TAContractForm(initial=initial)

    form.fields['position_number'].choices = position_choices       
    for f in formset:
        f.fields['course'].choices = course_choices
    
    context = {'form': form, 'formset': formset, 'posting': posting, 'editing': editing,
               'old_status': old_status, 'contract': contract, 'application': application,
               'userid': userid}
    return render(request, 'ta/edit_contract.html',context)

def _copy_posting_defaults(source, destination):
    """
    Copy some defaults from source posting to the destination
    """
    destination.set_salary(source.salary())
    destination.set_scholarship(source.scholarship())
    destination.set_accounts(source.accounts())
    destination.set_bu_defaults(source.bu_defaults())
    destination.set_payperiods(source.payperiods())
    destination.set_contact(source.contact().id)
    # TODO: also copy Skill values

@requires_role("TAAD")
def edit_posting(request, post_slug=None):
    unit_choices = [(u.id, unicode(u)) for u in request.units]
    account_choices = [(a.id, "%s (%s)" % (a.position_number, a.title)) for a in Account.objects.filter(unit__in=request.units)]
    contact_choices = [(r.person.id, "%s" % (r.person.name())) for r in Role.objects.filter(unit__in=request.units)]
    contact_choices = list(set(contact_choices))

    today = datetime.date.today()
    semester_choices = [(s.id, unicode(s)) for s in Semester.objects.filter(start__gt=today).order_by('start')]
    # TODO: display only relevant semester/unit offerings (with AJAX magic)
    offerings = CourseOffering.objects.filter(owner__in=request.units).select_related('course')
    excluded_choices = list(set(((u"%s (%s)" % (o.course,  o.title), o.course_id) for o in offerings)))
    excluded_choices.sort()
    excluded_choices = [(cid,label) for label,cid in excluded_choices]
    
    if post_slug:
        # editing existing
        posting = get_object_or_404(TAPosting, slug=post_slug)
        if posting.unit not in request.units:
            ForbiddenResponse(request, 'You cannot access this posting')
        editing = True
    else:
        # creating new
        posting = TAPosting()
        editing = False

        # populate from previous semester if possible
        old_postings = TAPosting.objects.filter(unit__in=request.units).order_by('-semester')
        if old_postings:
            old = old_postings[0]
            _copy_posting_defaults(old, posting)
        else:
            # heuristic default: non-lecture sections, except distance, are excluded
            default_exclude = set((o.course_id for o in offerings.filter(component="SEC").exclude(section__startswith="C")))
            posting.config['excluded'] = default_exclude
            posting.config['contact'] = Person.objects.get(userid=request.user.username).id
    
    if request.method == "POST":
        form = TAPostingForm(data=request.POST, instance=posting)
        form.fields['unit'].choices = unit_choices
        form.fields['semester'].choices = semester_choices
        form.fields['excluded'].choices = excluded_choices
        form.fields['contact'].choices = contact_choices
        for f in form.fields['accounts'].fields:
            f.choices = account_choices
        for w in form.fields['accounts'].widget.widgets:
            w.choices = account_choices
        if form.is_valid():
            form.instance.slug = None
            form.save()
            found_skills = set()
            for s in form.cleaned_data['skills']:
                s.posting = form.instance
                s.save()
                found_skills.add(s.id)
            
            # if any skills were dropped, remove them
            Skill.objects.filter(posting=form.instance).exclude(id__in=found_skills).delete()
            
            l = LogEntry(userid=request.user.username,
                  description="Edited TAPosting for %s in %s." % (form.instance.unit, form.instance.semester),
                  related_object=form.instance)
            l.save()
            if editing:
                messages.success(request, "Edited TA posting for %s in %s." % (form.instance.unit, form.instance.semester))
            else:
                messages.success(request, "Created TA posting for %s in %s." % (form.instance.unit, form.instance.semester))
            return HttpResponseRedirect(reverse('ta.views.view_postings', kwargs={}))
    else:
        form = TAPostingForm(instance=posting)
        form.fields['unit'].choices = unit_choices
        form.fields['semester'].choices = semester_choices
        form.fields['excluded'].choices = excluded_choices
        form.fields['contact'].choices = contact_choices
        for f in form.fields['accounts'].fields:
            f.choices = account_choices
        for w in form.fields['accounts'].widget.widgets:
            w.choices = account_choices

    context = {'form': form, 'editing': editing, 'posting': posting}
    return render(request, 'ta/edit_posting.html', context)


@requires_role("TAAD")
def posting_admin(request, post_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug)

    context = {'posting': posting}
    return render(request, 'ta/posting_admin.html', context)


@requires_role("TAAD")
def bu_formset(request, post_slug):
    """
    AJAX method to build the formset for a particular level
    
    Called in edit_bu.html to dynmically change formset as selected
    """
    posting = get_object_or_404(TAPosting, slug=post_slug)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this page')
    
    if 'level' not in request.GET:
        return ForbiddenResponse(request, 'must give level')
    level = request.GET['level']
    
    # populate existing values if exist
    initial=[]
    defaults = posting.bu_defaults()
    if level in defaults:
        initial = [{'students': s, 'bus': b} for s,b in defaults[level]]
    formset = BUFormSet(prefix="set"+level, initial=initial)
    
    context = {'level': level, 'formset': formset}
    return render(request, 'ta/bu_formset.html', context)
    

@requires_role("TAAD")
def edit_bu(request, post_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this page')

    formset = None # used in bu_formset.html as defaults if present; AJAX magic if not
    level = None
    if request.method == "POST":
        form = TAPostingBUForm(request.POST)
        if form.is_valid():
            level = form.cleaned_data['level']
            formset = BUFormSet(request.POST, prefix="set"+level)
            if formset.is_valid():
                bus = [(d['students'], d['bus']) for d in formset.cleaned_data if 'bus' in d and 'students' in d]
                bus.sort()
                defaults = posting.bu_defaults()
                defaults[level] = bus
                posting.set_bu_defaults(defaults)
                posting.save()
                
                l = LogEntry(userid=request.user.username,
                  description=u"Edited BU defaults for %s, level %s." % (posting, level),
                  related_object=posting)
                l.save()
                messages.success(request, u"Updated BU defaults for %s, %s-level." % (posting, level))
    else:
        form = TAPostingBUForm()

    context = {'form': form, 'formset': formset, 'posting': posting, 'level': level}
    return render(request, 'ta/edit_bu.html',context)


@requires_role("TAAD")
def generate_csv(request, post_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this page')
    
    all_offerings = CourseOffering.objects.filter(semester=posting.semester, owner=posting.unit)
    excl = set(posting.excluded())
    offerings = [o for o in all_offerings if o.course_id not in excl]
  
    course_prefs = []
    for o in offerings:
        cp = CoursePreference.objects.filter(course=o.course)
        for c in cp:
            course_prefs.append(c)
    
    # Collect course prefs from same application and put them
    # in sub lists that correspond to a csv row
    app_course_list = []
    while len(course_prefs) != 0:
        app = course_prefs[0].app
        app_course_list.append([p for p in course_prefs if p.app == app])
        course_prefs = [p for p in course_prefs if p.app != app] 

    filename = str(posting.slug) + '.csv'
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s'% filename
    csvWriter = csv.writer(response)
    
    #First csv row, all the course names
    off = [str(o.course) + ' ' + str(o.section) for o in offerings]
    off.insert(0,'')
    csvWriter.writerow(off)

    #Construct remaining csv rows of applicant name and course rank
    csv_rows = []
    csv_row = []
    for cp in app_course_list:
        name = cp[0].app.person.last_name + ', ' + cp[0].app.person.first_name
        csv_row.append(name)

        for o in offerings:
            found = False
            for c in cp:
                if o.course == c.course:
                    csv_row.append(c.rank)
                    found = True
                    cp.remove(c)
            if not found:
                csv_row.append('')
        csv_rows.append(csv_row)
        csv_row = []

    csv_rows.sort()
    for row in csv_rows:
        csvWriter.writerow(row)

    return response

@requires_role("TAAD")
def view_financial(request, post_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this page')
    
    all_offerings = CourseOffering.objects.filter(semester=posting.semester, owner=posting.unit)
    # ignore excluded courses
    excl = set(posting.excluded())
    offerings = [o for o in all_offerings if o.course_id not in excl]
    excluded = [o for o in all_offerings if o.course_id in excl]
    
    context = {'posting': posting, 'offerings': offerings, 'excluded': excluded}
    return render(request, 'ta/view_financial.html', context) 
