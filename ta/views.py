from django.http import HttpResponseRedirect#, HttpResponse
from django.shortcuts import get_object_or_404, render#, render_to_response, 
from django.core.urlresolvers import reverse
from courselib.auth import requires_course_staff_by_slug, requires_role, \
    is_course_staff_by_slug, has_role, ForbiddenResponse
from django.contrib.auth.decorators import login_required
from ta.models import TUG, TAApplication, Skill
from coredata.models import Member, Role, CourseOffering, Person
from ta.forms import CoursePreferenceForm, TAApplicationForm, TUGForm

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
        components = course.component
        has_lab_or_tut = False
        for component in components:
            if component == "LAB" or component == "TUT":
                has_lab_or_tut = True
            
        if request.method == "POST":
            form = TUGForm(data=request.POST)
            if form.is_valid():
                tug = form.save(False)
                # TODO: set the ta member once it's no longer included in the form
                tug.save()
                return HttpResponseRedirect(reverse(all_tugs, args=[course.slug]))
        else:
            form = TUGForm(offering=course,userid=userid)
        
        context = {'member':member,
                   'course':course,
                   'form':form,
                   'userid':userid,
                   'hasLabOrTut': has_lab_or_tut}
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
        tug = TUG.objects.get(member=member)
        max_hours = tug.base_units * 42
        total_hours = 0 
        for field, params in tug.config.iteritems():
            if not field == 'other2':
                total_hours += params['total']
        
        context = {'tug': tug, 'ta':member, 'course':course, 'maxHours':max_hours, 'totalHours':total_hours}
        return render(request, 'ta/view_tug.html',context)

@requires_course_staff_by_slug
def edit_tug(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=userid)
    tug = TUG.objects.get(member=member)
    if (request.method=="POST"):
        tug_form = TUGForm(request.POST)
    else:
        tug_form = TUGForm(instance=tug)
    context = {'course':course, 'ta':member.person, 'form': tug_form, 'tug':tug }
    
    return render(request, 'ta/edit_tug.html',context)

@login_required
def new_application(request):
    if request.method == "POST":
        ta_form = TAApplicationForm(request.POST, prefix='ta')
        course_form = CoursePreferenceForm(request.POST, prefix='course')
        if ta_form.is_valid():
        #if ta_form.is_valid() and course_form.is_valid():
            person = get_object_or_404(Person, userid=request.user.username)
            app = ta_form.save(commit=False)
            app.person = person
            app.save()
    
            course = course_form.save(commit=False)
            course.app = TAApplication.objects.get(id=app.id)
            course.save()
    
            ta_form.save_m2m()
        else:
            print ta_form
            print "ta form valid:" + str(ta_form.is_valid())
            print "course form valid:" + str(course_form.is_valid())
        #TODO: figure out propper redirect
        return HttpResponseRedirect('')

    else:
        ta_prefix = 'ta'
        ta_form = TAApplicationForm(prefix = ta_prefix)
        course_form = CoursePreferenceForm(prefix = 'course')
        skill_names = Skill.objects.order_by('name').values('name').distinct() 
        skills = Skill.objects.order_by('name') 
        return render(request, 'ta/new_application.html', {'ta_form':ta_form, 'ta_prefix':ta_prefix, 'course_form':course_form, 'skill_names':skill_names, 'skills':skills})

@login_required
def all_applications(request):
    applications = TAApplication.objects.all()
    return render(request, 'ta/all_applications.html', {'applications':applications})

@login_required
def view_application(request, app_id):
    application = TAApplication.objects.get(id=app_id)
    return render(request, 'ta/view_application.html', {'application':application})
