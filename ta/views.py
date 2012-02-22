from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.core.urlresolvers import reverse
from django.contrib import messages
from courselib.auth import requires_course_staff_by_slug, requires_role, \
    is_course_staff_by_slug, has_role, ForbiddenResponse
from django.contrib.auth.decorators import login_required
from ta.models import TUG, Skill, TAApplication, TAPosting, TAContract, TACourse, CoursePreference, CampusPreference
from ra.models import Account
from coredata.models import Member, Role, CourseOffering, Person, Semester
from ta.forms import TUGForm, TAApplicationForm, TAContractForm, CoursePreferenceForm, \
    TAPostingForm, TAPostingBUForm, BUFormSet, TACourseForm
from log.models import LogEntry
from django.forms.models import inlineformset_factory
from django.forms.formsets import formset_factory
import datetime

@requires_course_staff_by_slug
def index_page(request, course_slug):
    if is_course_staff_by_slug(request, course_slug):
        return render(request, 'ta/index.html',{})
    else:
        return ForbiddenResponse(request)
        
@login_required
def all_tugs(request, course_slug):
    if is_course_staff_by_slug(request, course_slug):
        return _all_tugs_staff(request, course_slug)
    # to redirect department admins if they somehow accessed all tugs from courses page
    elif has_role("ADMN",request):
        return _all_tugs_admin(request)
    else:
        return ForbiddenResponse(request)

# wrapper function for url mapping
@requires_role("ADMN")
def all_tugs_admin(request):
    return _all_tugs_admin(request)

# zip tas and tugs together
# basically performs a left outer join between tas and tugs
def tryget(member):
    try:
        return TUG.objects.get(member=member)
    except(TUG.DoesNotExist):
        return None
    
#@requires_course_staff_by_slug
def _all_tugs_staff(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    tas = Member.objects.filter(offering=course, role="TA")
    current_user = Member.objects.get(person__userid=request.user.username, offering=course)
    #If a TA is accessing, only his/her own TUG should be viewable
    not_ta = True;
    if current_user in tas:
        tas = tas.filter(person__userid=current_user.person.userid)
        not_ta = False;
    tas_with_tugs = [(ta, tryget(ta)) for ta in tas]
    
    context = {
           'tas_with_tugs':tas_with_tugs,
           'course':course,
           'not_ta':not_ta
            }
    
    return render(request, 'ta/all_tugs.html', context)
        
#@requires_role("ADMN")
def _all_tugs_admin(request):
    unit = Role.objects.get(person__userid=request.user.username).unit
    courses = CourseOffering.objects.filter(owner=unit) # TO DO: Make this reference the CourseOffering's "Owner" field once it's been added
    tas = Member.objects.filter(offering__in=courses, role="TA")
    tas_with_tugs = [(ta, tryget(ta)) for ta in tas]

    context = {
               'tas_with_tugs':tas_with_tugs,
               'unit':unit,
               'courses':courses
                }
    
    return render(request, 'ta/all_tugs_admin.html', context)


@requires_course_staff_by_slug    
def new_tug(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=userid)
    curr_user_role = Member.objects.get(person__userid=request.user.username,offering=course).role
    
    # TAs should not be creating TUGs
    if(curr_user_role =="TA" and not userid==request.user.username ): 
        return ForbiddenResponse(request)
    else:
        # Nothing is done as of now until further details as to how to "pre-fill" 
        # #158    TUG: courses with lab sections should be pre-filled as appropriate
        has_lab_or_tut = course.labtut()
            
        if request.method == "POST":
            form = TUGForm(data=request.POST, offering=course,userid=userid)
            if form.is_valid():
                tug = form.save(False)
                # TODO: set the ta member once it's no longer included in the form
                tug.save()
                return HttpResponseRedirect(reverse(view_tug, args=(course.slug, userid)))
        else:
            form = TUGForm(offering=course,userid=userid)
        
        context = {'ta':member.person,
                   'course':course,
                   'form':form,
                   'userid':userid,
                   #'hasLabOrTut': has_lab_or_tut
                   }
        return render(request,'ta/new_tug.html',context)

@requires_course_staff_by_slug    
def view_tug(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=userid)
    curr_user_role = Member.objects.get(person__userid=request.user.username,offering=course).role
    
    #If the currently logged in user is a TA for the course and is viewing a TUG for another TA, show forbidden message
    if(curr_user_role =="TA" and not userid==request.user.username ): 
        return ForbiddenResponse(request)
    else:
        course = get_object_or_404(CourseOffering, slug=course_slug)
        member = get_object_or_404(Member, offering=course, person__userid=userid)
        tug = get_object_or_404(TUG, member=member)
        max_hours = tug.base_units * 42
        total_hours = sum(params.get('total',0) for _, params in tug.config.iteritems())
        
        context = {'tug': tug, 'ta':member, 'course':course, 'maxHours':max_hours, 'totalHours':total_hours}
        return render(request, 'ta/view_tug.html',context)

@requires_course_staff_by_slug
def edit_tug(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=userid)
    tug = get_object_or_404(TUG,member=member)
    if (request.method=="POST"):
        form = TUGForm(request.POST, instance=tug)
        if form.is_valid():
            tug = form.save(False)
            # TODO: set the ta member once it's no longer included in the form
            tug.save()
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
    CoursesFormSet = formset_factory(CoursePreferenceForm, extra=1, max_num=10)
    if request.method == "POST":
        ta_form = TAApplicationForm(request.POST, prefix='ta')
        courses_formset = CoursesFormSet(request.POST)
        if ta_form.is_valid() and courses_formset.is_valid():
            person = get_object_or_404(Person, userid=request.user.username)
            app = ta_form.save(commit=False)
            app.posting = posting
            app.person = person
            app.save()

            #Add every skill to application
            skill_count = Skill.objects.filter(unit=posting.unit.id).values('name').distinct().count()
            for i in range(1,skill_count+1):
                app.skills.add(request.POST['skills'+str(i)])
            
            #Add each campus preference to application
            campus_count = CampusPreference.objects.values('campus').distinct().count()
            for i in range(1,campus_count):
                app.campus_preferences.add(request.POST['campus_preference'+str(i)])
    
            ta_form.save_m2m()

            application = TAApplication.objects.get(id=app.id)
            for form in courses_formset:
                course = form.save(commit=False)
                course.app = application
                course.save()
            return HttpResponseRedirect(reverse('ta.views.view_application', kwargs={'app_id':app.id}))

        else:
            print ta_form
            print "ta form valid:" + str(ta_form.is_valid())
            #print "course form valid:" + str(course_form.is_valid())
        #TODO: figure out propper redirect
        return HttpResponseRedirect('')

    elif request.is_ajax():
        # TO DO: Update formset to correct number of forms displayed
        return HttpResponse("AJAX Completed") #return updated form.
    else:
        courses_formset = CoursesFormSet()
        for f in courses_formset:
            course_choices = [(c.id, unicode(c)) for c in posting.selectable_courses()]
            f.fields['course'].choices = course_choices
        ta_form = TAApplicationForm(prefix='ta')
        campus_names = CampusPreference.objects.order_by('campus').values('campus').distinct() 
        campus_preferences = CampusPreference.objects.all()
        skill_names = Skill.objects.filter(unit=posting.unit).order_by('name').values('name').distinct() 
        skills = Skill.objects.filter(unit=posting.unit).order_by('name','level')
        context = {
                    'posting':posting,
                    'ta_form':ta_form,
                    'courses_formset':courses_formset,
                    'campus_names':campus_names,
                    'campus_preferences':campus_preferences,
                    'skill_names':skill_names,
                    'skills':skills
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

@login_required
def view_application(request, app_id):
    
    application = TAApplication.objects.get(id=app_id)
    roles = Role.objects.filter(role="TAAD", person__userid=request.user.username)
   
    #Only TA Administrator or owner of application can view it
    if application.person.userid != request.user.username:
        units = [r.unit for r in roles]
        if roles.count() == 0:
            return ForbiddenResponse(request, 'You cannot access this posting')
        elif application.posting.unit not in units:
            return ForbiddenResponse(request, 'You cannot access this posting')
   
    courses = CoursePreference.objects.filter(app=app_id)
    return render(request, 'ta/view_application.html', {'application':application, 'courses':courses})

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
def all_contracts(request):
    contracts = TAContract.objects.all()
    postings = TAPosting.objects.filter(unit__in=request.units)
    return render(request, 'ta/all_contracts.html', {'contracts':contracts, 'postings':postings})

@requires_role("TAAD")
def new_contract(request, post_slug):
    posting = get_object_or_404(TAPosting, slug=post_slug)
    if posting.unit not in request.units:
        ForbiddenResponse(request, 'You cannot access this posting')
    course_choices = [('','---------')] + [(c.id, c.name()) for c in posting.selectable_offerings()]
    position_choices = [(a.id, a.position_number) for a in Account.objects.filter(unit=posting.unit)]
    TACourseFormset = inlineformset_factory(TAContract, TACourse, extra=3, can_delete=False, form=TACourseForm)
    contract = TAContract()
    formset = TACourseFormset(instance=contract)
    
    if request.method == "POST":
        form = TAContractForm(request.POST)
        
        if request.is_ajax():
            if('appt_cat' in request.POST):
                index = posting.cat_index(request.POST['appt_cat'])
                results = posting.config['salary'][index] + ',' + posting.config['scholarship'][index]
                return HttpResponse(results)
            if('course' in request.POST):
                course = request.POST['course']
                co = get_object_or_404(CourseOffering, pk=course)
                req_bu = posting.required_bu(co)
                return HttpResponse(req_bu)
        elif form.is_valid():
            contract = form.save(commit=False)
            formset = TACourseFormset(request.POST, instance=contract)
            if formset.is_valid():
                contract.ta_posting = posting
                contract.pay_per_bu = request.POST['pay_per_bu']
                contract.scholarship_per_bu = request.POST['scholarship_per_bu']
                contract.pay_start = form.cleaned_data['pay_start']
                contract.pay_end = form.cleaned_data['pay_end']
                contract.created_by = Person.objects.get(userid = request.user.username)
                contract.save()
                formset.save()
                messages.success(request, "Created TA Contract for %s for %s." % (contract.applicant, posting))
                return HttpResponseRedirect(reverse(all_contracts))
    
    else:   
        form = TAContractForm(instance=contract)
        formset = TACourseFormset(instance=contract)
        form = TAContractForm(initial={'pay_start': posting.config['start'], 'pay_end': posting.config['end']})
    
    form.fields['position_number'].choices = position_choices       
    for f in formset:
        f.fields['course'].widget.attrs['class']  = 'course_select'
        f.fields['bu'].widget.attrs['value'] = 0
    
    context = {'form': form, 'formset': formset, 'posting': posting, 'config': posting.config}
    return render(request, 'ta/new_contract.html',context)

def _copy_posting_defaults(source, destination):
    """
    Copy some defaults from source posting to the destination
    """
    destination.set_salary(source.salary())
    destination.set_scholarship(source.scholarship())
    destination.set_bu_defaults(source.bu_defaults())
    destination.set_payperiods(source.payperiods())

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
