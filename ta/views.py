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
from coredata.models import Member, Role, CourseOffering, Person, Semester
from ta.forms import TUGForm, TAApplicationForm, TAContractForm, CoursePreferenceForm, \
    TAPostingForm, TAPostingBUForm, BUFormSet, TACourseForm, BaseTACourseFormSet, AssignBUForm
from log.models import LogEntry
from django.forms.models import inlineformset_factory
from django.forms.formsets import formset_factory
import datetime, decimal

#@requires_course_staff_by_slug
@login_required
def index_page(request, course_slug):
    return HttpResponseRedirect(reverse(all_tugs, args=(course_slug,)))
    #~ if is_course_staff_by_slug(request, course_slug):
        #~ return render(request, 'ta/index.html',{})
    #~ else:
        #~ return ForbiddenResponse(request)

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
    #TODO: maybe use filter?
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

@login_required
def new_application(request, post_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug)
    course_choices = [(c.id, unicode(c)) for c in posting.selectable_courses()]
    used_campuses = set((vals['campus'] for vals in posting.selectable_offerings().order_by('campus').values('campus').distinct()))
    skills = Skill.objects.filter(posting=posting)
    CoursesFormSet = formset_factory(CoursePreferenceForm, extra=1, max_num=10)
    
    person = get_object_or_404(Person, userid=request.user.username)
    existing_app = TAApplication.objects.filter(person=person, posting=posting)
    if existing_app.count() > 0: 
        messages.success(request, "You have already applied for the %s %s posting." % (posting.unit, posting.semester))
        return HttpResponseRedirect(reverse('ta.views.view_application', kwargs={'app_id':existing_app[0].id}))
        

    if request.method == "POST":
        ta_form = TAApplicationForm(request.POST, prefix='ta')
        courses_formset = CoursesFormSet(request.POST)
        for f in courses_formset:
            f.fields['course'].choices = course_choices

        if ta_form.is_valid() and courses_formset.is_valid():
            app = ta_form.save(commit=False)
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
            return HttpResponseRedirect(reverse('ta.views.view_application', kwargs={'app_id':app.id}))
        
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
        courses_formset = CoursesFormSet()
        for f in courses_formset:
            f.fields['course'].choices = course_choices
        ta_form = TAApplicationForm(prefix='ta')
        campus_preferences = [(lbl, name, 'WIL') for lbl,name in CAMPUS_CHOICES if lbl in used_campuses]
        skill_values = [(s.position, s.name, 'NONE') for s in skills]

    context = {
                    'posting':posting,
                    'ta_form':ta_form,
                    'courses_formset':courses_formset,
                    'campus_preferences':campus_preferences,
                    'campus_pref_choices':PREFERENCE_CHOICES,
                    'skill_values': skill_values,
                    'skill_choices': LEVEL_CHOICES,
                  }
    return render(request, 'ta/new_application.html', context)

@requires_role("TAAD")
def all_applications(request):
    roles = Role.objects.filter(role="TAAD", person__userid=request.user.username)
    units = [r.unit for r in roles]
    postings = TAPosting.objects.filter(unit__in=units)
    applications = TAApplication.objects.filter(posting__in=postings)
    context = {
            'units':units,
            'applications':applications,
            }
    return render(request, 'ta/all_applications.html', context)

# TODO: shouldn't be visible to all users
@login_required
def view_application(request, app_id):
    
    application = get_object_or_404(TAApplication, id=app_id)
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
        ForbiddenResponse(request, 'You cannot access this posting')
    
    apps = TAApplication.objects.filter(posting=posting)
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
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    course_prefs = CoursePreference.objects.filter(course=offering.course) 
    apps = []
    campus_prefs = []
    initial = []

    for p in course_prefs:
        apps.append(p.app)
        campus_preference = CampusPreference.objects.get(app=p.app, campus=offering.campus)
        campus_prefs.append(campus_preference)
        initial.append({'rank': p.app.rank})

    AssignBUFormSet = formset_factory(AssignBUForm)
    
    #Save ranks and BU's
    if request.method == "POST":
        formset = AssignBUFormSet(request.POST)
        for i in range(0, len(apps)):
            apps[i].rank = formset[i]['rank'].value()
            apps[i].save()

    else: 
        formset = AssignBUFormSet(initial=initial)
 
    context = {'formset':formset, 'posting':posting, 'offering':offering, 'applications': apps, 'course_preferences': course_prefs, 'campus_preferences':campus_prefs}
    return render(request, 'ta/assign_bu.html', context) 

@requires_role("TAAD")
def all_contracts(request):
    contracts = TAContract.objects.all()
    postings = TAPosting.objects.filter(unit__in=request.units)
    return render(request, 'ta/all_contracts.html', {'contracts':contracts, 'postings':postings})

@requires_role("TAAD")
def view_contract(request, contract_id):
    contract = get_object_or_404(TAContract, pk=contract_id)
    return render(request, 'ta/view_contract.html', {'contract':contract})

@requires_role("TAAD")
def edit_contract(request, post_slug, contract_id=None):
    posting = get_object_or_404(TAPosting, slug=post_slug)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this posting')
    course_choices = [('','---------')] + [(c.id, c.name()) for c in posting.selectable_offerings()]
    position_choices = [(a.id, a.position_number) for a in Account.objects.filter(unit=posting.unit)]
    app_choices = [('','---------')] + [(p.id, unicode(p)) for p in Person.objects.exclude(Q(pk__in=posting.tacontract_set.all().values_list('applicant', flat=True)) )]
        
    #number of course form to populate
    num = 3
    if contract_id:
        # editing existing contract
        contract = get_object_or_404(TAContract, id=contract_id)
        num = num - contract.tacourse_set.all().count()
        editing = True
    else:
        # creating new contract
        contract = TAContract()
        editing = False

    TACourseFormset = inlineformset_factory(TAContract, TACourse, extra=num, can_delete=editing, form=TACourseForm, formset=BaseTACourseFormSet)
    formset = TACourseFormset(instance=contract)
    
    if request.method == "POST":
        form = TAContractForm(request.POST, instance=contract)
        
        if request.is_ajax():
            if('appt_cat' in request.POST):
                index = posting.cat_index(request.POST['appt_cat'])
                results = posting.config['salary'][index] + ',' + posting.config['scholarship'][index]
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
                if(len(co.config) > 0 and co.config['labtut']):
                    results += ',OML'
                else:
                    results += ',OM'
                return HttpResponse(results)
            if('applicant' in request.POST):
                results = ''
                app = TAApplication.objects.filter(person=request.POST['applicant'], posting=posting)
                if(app.count() > 0):              
                    results = app[0].sin, ',', app[0].category
                    print results
                else:
                    #try to find applicaion from other postings, grab from latest
                    app = TAApplication.objects.filter(person=request.POST['applicant']).order_by('-id')
                    
                    if(app.count() > 0):
                        results = app[0].sin, ',', app[0].category
                return HttpResponse(results)
        elif form.is_valid():
            contract = form.save(commit=False)
            formset = TACourseFormset(request.POST, instance=contract)
            if formset.is_valid():
                contract.ta_posting = posting
#                contract.pay_per_bu = request.POST['pay_per_bu']
                #contract.scholarship_per_bu = request.POST['scholarship_per_bu']
                contract.pay_per_bu = form.cleaned_data['pay_per_bu']
                contract.pay_start = form.cleaned_data['pay_start']
                contract.pay_end = form.cleaned_data['pay_end']
                contract.created_by = request.user.username
                contract.updated_at = datetime.datetime.now()
                contract.save()
                formset.save()
                if not editing:
                    messages.success(request, "Created TA Contract for %s for %s." % (contract.applicant, posting))
                else:
                    messages.success(request, "Edited TA Contract for %s for %s." % (contract.applicant, posting))
                return HttpResponseRedirect(reverse(all_contracts))
    else:   
        form = TAContractForm(instance=contract) 
        formset = TACourseFormset(instance=contract)
        if not editing:
            form = TAContractForm(initial={'pay_start': posting.start(), 'pay_end': posting.end(), 'deadline': posting.deadline()})
            form.fields['applicant'].choices = app_choices
    
    form.fields['position_number'].choices = position_choices       
    for f in formset:
        f.fields['course'].widget.attrs['class']  = 'course_select'
        f.fields['description'].widget.attrs['class']  = 'desc_select'
        f.fields['bu'].widget.attrs['class']  = 'bu_inp'
        f.fields['course'].choices = course_choices
    
    context = {'form': form, 'formset': formset, 'posting': posting, 'config': posting.config, 'editing': editing, 'contract': contract}
    return render(request, 'ta/edit_contract.html',context)

def _copy_posting_defaults(source, destination):
    """
    Copy some defaults from source posting to the destination
    """
    destination.set_salary(source.salary())
    destination.set_scholarship(source.scholarship())
    destination.set_bu_defaults(source.bu_defaults())
    destination.set_payperiods(source.payperiods())
    # TODO: also copy Skill values

@requires_role("TAAD")
def edit_posting(request, post_slug=None):
    unit_choices = [(u.id, unicode(u)) for u in request.units]

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
    
    if request.method == "POST":
        form = TAPostingForm(request.POST, instance=posting)
        form.fields['unit'].choices = unit_choices
        form.fields['semester'].choices = semester_choices
        form.fields['excluded'].choices = excluded_choices
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
    
    context = {'form': form, 'editing': editing, 'posting': posting}
    return render(request, 'ta/edit_posting.html', context)


@requires_role("TAAD")
def bu_formset(request, post_slug):
    """
    AJAX method to build the formset for a particular level
    
    Called in edit_bu.html to dynmically change formset as selected
    """
    posting = get_object_or_404(TAPosting, slug=post_slug)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this posting')
    
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
        ForbiddenResponse(request, 'You cannot access this posting')

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
