from django.contrib.auth.decorators import login_required
from coredata.models import Member, CourseOffering, Person
from django.shortcuts import render_to_response, get_object_or_404#, redirect
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from courselib.auth import requires_course_by_slug,requires_course_staff_by_slug
from submission.forms import *
from courselib.auth import is_course_staff_by_slug, is_course_member_by_slug
from submission.models import *
from django.core.urlresolvers import reverse
from contrib import messages
from datetime import *
from marking.views import marking
from django.core.servers.basehttp import FileWrapper
import zipfile
import tempfile
import os

@login_required
def index(request):
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    return render_to_response("submission/index.html", {'memberships': memberships}, context_instance=RequestContext(request))


@login_required
def show_components(request, course_slug, activity_slug):
    #if course staff
    if is_course_staff_by_slug(request.user, course_slug):
        return _show_components_staff(request, course_slug, activity_slug)
    #else course member
    elif is_course_member_by_slug(request.user, course_slug):
        return _show_components_student(request, course_slug, activity_slug)
    #else not found, return 403
    else:
        resp = render_to_response('403.html', context_instance=RequestContext(request))
        resp.status_code = 403
        return resp
    
#student submission main page
#may be viewed by a staff
def _show_components_student(request, course_slug, activity_slug, userid=None, template="component_view.html"):
    """
    Show all the component submission history of this activity
    """
    if userid == None:
        userid = request.user.username
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    student = get_object_or_404(Person, userid=userid)

    submitted_pair_list = _get_current_submission(userid, activity)
    owner = None

    #calculate latest submission
    submit_time = None
    for pair in submitted_pair_list:
        if pair[1] != None:
            try:
                if submit_time == None:
                    submit_time = datetime.now()
            except:
                pass
            if pair[1].submission.owner != None:
                owner = pair[1].submission.owner.person
            if submit_time > pair[1].submission.created_at:
                submit_time = pair[1].submission.created_at

    late = None
    if submit_time != None and submit_time > activity.due_date:
        late = submit_time - activity.due_date

    #when no submittable component
    if len(submitted_pair_list) == 0:
        messages.add_message(request, messages.WARNING, 'There is no submittable component of this activity.')

    return render_to_response("submission/" + template,
        {"course":course, "activity":activity, "submitted_pair":submitted_pair_list, "userid":userid, "submit_time":submit_time, "late":late, "student":student, "owner":owner},
        context_instance=RequestContext(request))

def _get_current_submission(userid, activity):
    """
    return a list of pair[component, latest_submission(could be None)]
    """
    component_list = select_all_components(activity)
    all_submitted = select_students_submitted_components(activity, userid)
    #TODO: group submission
    
    submitted_pair_list = []
    for component in component_list:
        pair = []
        pair.append(component)
        c = [sub for sub in all_submitted if sub.component == component]
        c.sort()
        if len(c) == 0:
            pair.append(None)
        else:
            pair.append(c[0])
        submitted_pair_list.append(pair)
    return submitted_pair_list

#student's submission page
@requires_course_by_slug
def add_submission(request, course_slug, activity_slug):
    """
    enable student to upload files to a activity
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    component_list = select_all_components(activity)
    component_list.sort()
    component_form_list=[]
    for component in component_list:
        if component.get_type() == 'URL':
            pair = []
            pair.append(component)
            pair.append(SubmittedURLForm(prefix=component.id))
            component_form_list.append(pair)
        elif component.get_type() == 'Archive':
            pair = []
            pair.append(component)
            pair.append(SubmittedArchiveForm(prefix = component.id))
            component_form_list.append(pair)
        elif component.get_type() == 'Cpp':
            pair = []
            pair.append(component)
            pair.append(SubmittedCppForm(prefix = component.id))
            component_form_list.append(pair)
        elif component.get_type() == 'Java':
            pair = []
            pair.append(component)
            pair.append(SubmittedJavaForm(prefix = component.id))
            component_form_list.append(pair)
        elif component.get_type() == 'PlainText':
            pair = []
            pair.append(component)
            pair.append(SubmittedPlainTextForm(prefix = component.id))
            component_form_list.append(pair)

    if request.method == 'POST':
        submission_list = []    # list all the submittedComponent submitted in the POST
        not_submitted_comp = []
        new_sub = StudentSubmission()   # the submission foreign key
        new_sub.activity = activity
        #TODO: test if the submission is a group or student submission then adit accordingly
        #new_sub.member = get_object_or_404(Member, {'person__userid':request.user.username, 'offering__slug': course_slug})
        member = Member.objects.filter(person__userid = request.user.username)
        new_sub.member = get_object_or_404(member, offering__slug = course_slug)
        for component in component_list:

            if component.get_type() == 'URL' :
                file = request.POST.get(str(component.id) + '-' + component.get_type().lower())
            elif component.get_type() == 'PlainText':
                file = request.POST.get(str(component.id) + '-' + 'text')
            else:
                file = request.FILES.get(str(component.id) + '-' + component.get_type().lower())
                print request.FILES
            print file
            if file == None:
                not_submitted_comp.append(component)
            else:
                if component.get_type() == 'URL':
                    sub = SubmittedURL()
                    sub.url = file
                elif component.get_type() == 'Archive':
                    sub = SubmittedArchive()
                    sub.archive = file
                elif component.get_type() == 'Cpp':
                    sub = SubmittedCpp()
                    sub.cpp = file
                elif component.get_type =='Java':
                    sub = SubmittedJava()
                    sub.java = file
                elif component.get_type() == 'PlainText':
                    sub = SubmittedPlainText()
                    sub.text = file
                new_sub.save()
                sub.submission = new_sub    #point to the submission foreign key
                sub.component = component
                submission_list.append(sub)
        #TODO: enable the file type tester!
        #print submission_list
        if submission_list != []:
           for submission in submission_list:
                submission.save()
        return HttpResponse("OK!")
        #return _submission_test(request, course_slug, activity_slug,submission_list, not_submitted_component)
        #)
    else:
        component_list = select_all_components(activity)
        return render_to_response("submission/submission_add.html",
        {'component_form_list': component_form_list, "course": course, "activity": activity},
        context_instance = RequestContext(request))

#student submission history page


@login_required
def show_components_submission_history(request, course_slug, activity_slug):
    userid = request.GET.get('userid')
    if userid==None:
        userid = request.user.username
    student = get_object_or_404(Person, userid=userid)
    #if not course_staff
    if not is_course_staff_by_slug(request.user, course_slug):
        #if not myself
        if not userid == request.user.username:
            return _return_403_dashboard(request, course_slug, activity_slug)
        #TODO: for group submission, allow the member in the same group to download
        
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    all_submitted_components = select_students_submitted_components(activity, userid)
    component_list = select_all_components(activity)
    empty_component = []
    for component in component_list:
        if select_students_submission_by_component(component, userid) == []:
            empty_component.append(component)
    return render_to_response("submission/submission_history_view.html", 
        {'submitted_component': all_submitted_components,'empty_component': empty_component, 'course':course, 'activity':activity},
        context_instance = RequestContext(request))

#staff submission configuratiton
@login_required
def _show_components_staff(request, course_slug, activity_slug):
    """
    Show all the components of this activity
    Responsible for updating position
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)

    #if POST, update the positions
    if request.method == 'POST':
        component_list = select_all_components(activity)
        counter = 0
        for component in component_list:
            counter = counter + 1
            t = request.POST.get('' + str(counter) + '_position');
            #in case t is not a number
            try:
                component.position = int(t)
                component.save()
            except:
                pass
        messages.add_message(request, messages.SUCCESS, 'Component positions updated.')
        return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))

    
    component_list = select_all_components(activity)
    return render_to_response("submission/component_view_staff.html",
        {"course":course, "activity":activity, "component_list":component_list},
        context_instance=RequestContext(request))


@requires_course_staff_by_slug
def confirm_remove(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    component_list = select_all_components(activity)
    
    #show confirm message
    del_id = request.GET.get('id')
    del_type = request.GET.get('type')
    component = None
    if del_id == None or del_type == None:
        #url is invalid
        pass
    else:
        #make sure type, id, and activity is correct
        for c in component_list:
            if str(c.get_type()) == del_type and str(c.id) == del_id and c.activity == activity:
                component = c
                break

    #if confirmed
    if request.method == 'POST' and component != None:
        component.delete()
        messages.add_message(request, messages.SUCCESS, 'Component "' +  component.title + '" removed.')
        return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))

    return render_to_response("submission/component_remove.html",
            {"course":course, "activity":activity, "component":component, "del_id":del_id},
            context_instance=RequestContext(request))



@requires_course_staff_by_slug
def edit_single(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    component_list = select_all_components(activity)

    #get component
    edit_id = request.GET.get('id')
    edit_type = request.GET.get('type')
    component = None
    if edit_id == None or edit_type == None:
        #url is invalid
        pass
    else:
        #make sure type, id, and activity is correct
        for c in component_list:
            if str(c.get_type()) == edit_type and str(c.id) == edit_id and c.activity == activity:
                component = c
                break
    #if component is invalid
    if component == None:
        messages.add_message(request, messages.ERROR, 'The component you specified is invalid.')
        return render_to_response("submission/component_edit_single.html",
            {"course":course, "activity":activity, "component":component},
            context_instance=RequestContext(request))

    #get type change
    type = request.GET.get('to_type')
    #if no type change
    if type == None:
        pass
    elif type == component.get_type():
        #no change
        return HttpResponseRedirect("?type="+type+"&id="+str(component.id))
    else:
    #if need to change type
        if type == 'Archive':
            new_component = ArchiveComponent()
        elif type == 'URL':
            new_component = URLComponent()
        elif type == 'Cpp':
            new_component = CppComponent()
        elif type == 'PlainText':
            new_component = PlainTextComponent()
        elif type == 'Java':
            new_component = JavaComponent()
        else:
            #to_type is invalid, just ignore
            new_component = component
        #copy a new component
        new_component.id = component.id
        new_component.activity = component.activity
        new_component.title = component.title
        new_component.description = component.description
        new_component.position = component.position
        #save new component
        component.delete()
        new_component.save()
        #refresh the form
        return HttpResponseRedirect("?type="+new_component.get_type()+"&id="+str(new_component.id))
        
    
    #make form
    form = None
    new_form = None
    if edit_type == 'Archive':
        form = ArchiveComponentForm(instance=component)
        new_form = ArchiveComponentForm(request.POST)
    elif edit_type == 'URL':
        form = URLComponentForm(instance=component)
        new_form = URLComponentForm(request.POST)
    elif edit_type == 'Cpp':
        form = CppComponentForm(instance=component)
        new_form = CppComponentForm(request.POST)
    elif edit_type == 'PlainText':
        form = PlainTextComponentForm(instance=component)
        new_form = PlainTextComponentForm(request.POST)
    elif edit_type == 'Java':
        form = JavaComponentForm(instance=component)
        new_form = JavaComponentForm(request.POST)
        
    #if form submitted
    if request.method == 'POST':
        if new_form.is_valid():
            new_component = new_form.save(commit=False)
            new_component.activity = activity
            new_component.id = component.id
            if new_component.position == None:
                count = len(select_all_components(activity))
                new_component.position = count*10 + 10
            new_component.save()
            messages.add_message(request, messages.SUCCESS, 'Component "' + new_component.title + '" successfully updated.')
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
        else:
            form = new_form
            messages.add_message(request, messages.ERROR, 'Please correct the errors in the form.')

    #render the page
    return render_to_response("submission/component_edit_single.html",
            {"course":course, "activity":activity, "component":component, "edit_id":edit_id,
             "type":edit_type, "form":form},
            context_instance=RequestContext(request))

@requires_course_staff_by_slug
def add_component(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)

    #default, Archive
    type = request.GET.get('type')
    if type == None:
        type = 'Archive'

    if type == 'Archive':
        form = ArchiveComponentForm()
        new_form = ArchiveComponentForm(request.POST)
    elif type == 'URL':
        form = URLComponentForm()
        new_form = URLComponentForm(request.POST)
    elif type == 'Cpp':
        form = CppComponentForm()
        new_form = CppComponentForm(request.POST)
    elif type == 'PlainText':
        form = PlainTextComponentForm()
        new_form = PlainTextComponentForm(request.POST)
    elif type == 'Java':
        form = JavaComponentForm()
        new_form = JavaComponentForm(request.POST)
    else:
        raise Http404()

    #if form is submitted, validate / add component
    if request.method == 'POST':
	#incoming_form = AddComponentForm(request.POST)
        if new_form.is_valid():
            #add component
            new_component = new_form.save(commit=False)
            new_component.activity = activity
            if new_component.position == None:
                count = len(select_all_components(activity))
                new_component.position = count*10 + 10
            new_component.save()
            messages.add_message(request, messages.SUCCESS, 'New component "' + new_component.title + '" successfully added.')
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
        else:
            messages.add_message(request, messages.ERROR, 'Please correct the errors in the form.')
            form = new_form
    return render_to_response("submission/component_add.html", 
        {"course":course, "activity":activity, "form":form, "type":type},
        context_instance=RequestContext(request))

@login_required
def download_file(request, course_slug, activity_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    
    type = request.GET.get('type') #targeted file type
    id = request.GET.get('id') #targeted submitted component id
    #student_id = request.GET.get('user-id') #targeted student
    group_id = request.GET.get('group-id') #targeted group

    #if not course_staff
    if not is_course_staff_by_slug(request.user, course_slug):
        #if not myself
        if not userid == request.user.username:
            return _return_403_dashboard(request, course_slug, activity_slug)
        #TODO: for group submission, allow the member in the same group to download

    # download as (file type + submitted id)
    if type == 'PlainText':
        text_component = get_object_or_404(SubmittedPlainText, id = id)
        return _download_text_file(text_component)
    if type == 'URL':
        url_component = get_object_or_404(SubmittedURL, id=id)
        return _download_url_file(url_component)
    if type == 'Archive':
        archive_component = get_object_or_404(SubmittedArchive, id=id)
        return _download_archive_file(archive_component)
    if type == 'Cpp':
        cpp_component = get_object_or_404(SubmittedCpp, id=id)
        return _download_cpp_file(cpp_component)
    if type == 'Java':
        java_component = get_object_or_404(SubmittedJava, id=id)
        return _download_java_file(java_component)

    #download current submission as a zip file for userid='id'
    if userid != None:
        #make sure student exists
        student = get_object_or_404(Person, userid=userid)
    else:
        get_object_or_404(Group, group_id)
        #TODO: group submission

    #TODO: modify the function to work for group submission
    submitted_pair_list = _get_current_submission(userid, activity)
    # if no submission, jump to the other page
    no_submission = True
    for pair in submitted_pair_list:
        if pair[1] != None:
            no_submission = False
            break
    if no_submission == True:
        return render_to_response("submission/download_error_no_submission.html",
        {"course":course, "activity":activity, "student":student},
        context_instance=RequestContext(request))

    return _generate_zip_file(submitted_pair_list, userid, activity_slug)


def _generate_zip_file(pair_list, userid, activity_slug):
    handle, filename = tempfile.mkstemp('.zip')
    os.close(handle)
    z = zipfile.ZipFile(filename, 'w', zipfile.ZIP_STORED)

    for pair in pair_list:
        type = pair[0].get_type()
        if type == 'PlainText':
            z.writestr(pair[0].slug+".txt", pair[1].text)
        if type == 'URL':
            content = '<html><head><META HTTP-EQUIV="Refresh" CONTENT="0; URL=' \
                        + pair[1].url + '"></head><body>' \
                        + 'If redirecting doesn\' work, click the link <a href="' \
                        + pair[1].url + '">' + pair[1].url + '</a>' \
                        + '</body></html> '
            z.writestr(pair[0].slug+".html", content)
        if type == 'Archive':
            name = pair[1].archive.name
            name = name[name.rfind('/')+1:]
            name = pair[0].slug + "_" + name
            z.write(pair[1].archive.path, name)
        if type == 'Cpp':
            name = pair[1].cpp.name
            name = name[name.rfind('/')+1:]
            name = pair[0].slug + "_" + name
            z.write(pair[1].cpp.path, name)
        if type == 'Java':
            name = pair[1].java.name
            name = name[name.rfind('/')+1:]
            name = pair[0].slug + "_" + name
            z.write(pair[1].java.path, name)
    z.close()

    file = open(filename, 'rb')
    response = HttpResponse(FileWrapper(file), mimetype='application/zip')
    response['Content-Disposition'] = 'attachment; filename=%s'% userid + "_" + activity_slug + ".zip"
    try:
        os.remove(filename)
    except OSError:
        print "HA!"
    return response

def _download_text_file(submission):
    """
    return a txt file attachment, the request contains a GET field 'id'
    """
    response = HttpResponse(submission.text, mimetype='text/plain')
    response['Content-Disposition'] = 'attachment; filename=%s' %\
        submission.submission.get_userid() + "_" + submission.component.slug + ".txt"
    return response

def _download_url_file(submission):
    """
    return a .html file with redirect information
    """
    content = '<html><head><META HTTP-EQUIV="Refresh" CONTENT="0; URL=' \
        + submission.url + '"></head><body>' \
        + 'If redirecting doesn\' work, click the link <a href="' \
        + submission.url + '">' + submission.url + '</a>' \
        + '</body></html> '
    response = HttpResponse(content, mimetype='text/html')
    response['Content-Disposition'] = 'attachment; filename=%s' %\
        submission.submission.get_userid() + "_" + submission.component.slug + ".html"
    return response

def _download_archive_file(submission):
    response = HttpResponse(submission.archive, mimetype='application/octet-stream')
    filename = submission.archive.name
    filename = filename[filename.rfind('/')+1:]
    response['Content-Disposition'] = 'attachment; filename=%s' %\
        submission.submission.get_userid() + "_" + submission.component.slug + "_" + filename
    return response

def _download_cpp_file(submission):
    response = HttpResponse(submission.cpp, mimetype='text/plain')
    filename = submission.cpp.name
    filename = filename[filename.rfind('/')+1:]
    response['Content-Disposition'] = 'attachment; filename=%s' %\
        submission.submission.get_userid() + "_" + submission.component.slug + "_" + filename
    return response

def _download_java_file(submission):
    response = HttpResponse(submission.java, mimetype='text/plain')
    filename = submission.java.name
    filename = filename[filename.rfind('/')+1:]
    response['Content-Disposition'] = 'attachment; filename=%s' %\
        submission.submission.get_userid() + "_" + submission.component.slug + "_" + filename
    return response

def _return_403_dashboard(request, course_slug, activity_slug):
    messages.add_message(request, messages.WARNING, "Your don't have permission to the resource you just requested.")
    response = HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
    return response

@requires_course_staff_by_slug
def show_student_submission_staff(request, course_slug, activity_slug, userid):
    return _show_components_student(request, course_slug, activity_slug, userid, "view_student_dashboard_staff.html")

@requires_course_staff_by_slug
def show_student_history_staff(request, course_slug, activity_slug, userid):
    return show_components_submission_history(request, course_slug, activity_slug, userid)

@requires_course_staff_by_slug
def take_ownership_and_mark(request, course_slug, activity_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    
    from_page = request.GET.get('from_page')
    activity_mark = request.GET.get('base_activity_mark')
    from_page_suffix = from_page and '&from_page=' + str(from_page) or ''
    activity_mark_suffix = activity_mark and '&base_activity_mark=' + str(activity_mark) or ''
    print activity_mark_suffix
    #TODO: group, ?group=group.id
    response = HttpResponseRedirect(reverse(marking, args=[course_slug, activity_slug]) + "?student=" + userid + activity_mark_suffix + from_page_suffix)
    
    component = select_students_submitted_components(activity, userid)
    #if it is taken by someone not me, show a confirm dialog
    if request.GET.get('confirm') == None:
        for c in component:
            if c.submission.owner != None and c.submission.owner.person.userid != request.user.username:
                return _override_ownership_confirm(request, course, activity, userid, c.submission.owner.person, activity_mark_suffix, from_page_suffix)
            
    for c in component:
        c.submission.set_owner(course, request.user.username)
    return response

def _override_ownership_confirm(request, course, activity, userid, old_owner, activity_suffix, from_suffix):
    student = get_object_or_404(Person, userid=userid)
    
    return render_to_response("submission/override_ownership_confirm.html",
        {"course":course, "activity":activity, "student":student, "old_owner":old_owner, "true":True,
        "activity_suffix":activity_suffix, "from_suffix":from_suffix},
        context_instance=RequestContext(request))
