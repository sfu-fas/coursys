from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from pages.models import Page, PageVersion, MEMBER_ROLES, ACL_ROLES
from pages.forms import EditPageForm, EditFileForm
from coredata.models import Member, CourseOffering
from log.models import LogEntry
from courselib.auth import requires_discipline_user, is_discipline_user, requires_role, requires_global_role, NotFoundResponse, ForbiddenResponse

def _check_allowed(request, offering, acl_value):
    """
    Check to see if the person is allowed to do this Page action.

    Returns Member object if possible; True if non-member who is allowed, or None if not allowed.
    """
    members = Member.objects.filter(person__userid=request.user.username, offering=offering)
    if not members:
        if acl_value=='ALL':
            return True
        else:
            return None
    m = members[0]
    if acl_value == 'ALL':
        return m
    elif m.role in MEMBER_ROLES[acl_value]:
        return m

    return None    

def index_page(request, course_slug):
    return view_page(request, course_slug, 'Index')

def all_pages(request, course_slug):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    member = _check_allowed(request, offering, 'ALL')
    
    if member and member!=True:
        pages = Page.objects.filter(offering=offering, can_read__in=ACL_ROLES[member.role])
        can_create = member.role in MEMBER_ROLES['STAF']
    else:
        pages = Page.objects.filter(offering=offering, can_read='ALL')
        can_create = False

    context = {'offering': offering, 'pages': pages, 'can_create': can_create}
    return render(request, 'pages/all_pages.html', context)

def view_page(request, course_slug, page_label):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    pages = Page.objects.filter(offering=offering, label=page_label)
    if not pages:
        # missing page: do something more clever than the 404
        member = _check_allowed(request, offering, 'STAF')
        can_create = bool(member)
        context = {'offering': offering, 'can_create': can_create, 'page_label': page_label}
        return render(request, 'pages/missing_page.html', context)
    else:
        page = pages[0]
    
    version = page.current_version()
    
    member = _check_allowed(request, offering, page.can_read)
    # check that we have an allowed member of the course (and can continue)
    if not member:
        return ForbiddenResponse(request, 'Not allowed to view this page')
    
    if request.user.is_authenticated():
       editor = _check_allowed(request, offering, page.can_write)
       can_edit = bool(editor)
    else:
       can_edit = False
    
    is_index = page_label=='Index'
    if is_index:
        # canonical-ize the index URL
        url = reverse(index_page, kwargs={'course_slug': course_slug})
        if request.path != url:
            return HttpResponseRedirect(url)
    
    context = {'offering': offering, 'page': page, 'version': version,
               'can_edit': can_edit, 'is_index': is_index}
    return render(request, 'pages/view_page.html', context)

def view_file(request, course_slug, page_label):
    return _get_file(request, course_slug, page_label, 'inline')
def download_file(request, course_slug, page_label):
    return _get_file(request, course_slug, page_label, 'attachment')

def _get_file(request, course_slug, page_label, disposition):
    """
    view for either inlinte viewing or downloading file contents
    """
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    page = get_object_or_404(Page, offering=offering, label=page_label)
    version = page.current_version()
    if not version.is_filepage():
        return NotFoundResponse(request)
    
    member = _check_allowed(request, offering, page.can_read)
    # check that we have an allowed member of the course (and can continue)
    if not member:
        return ForbiddenResponse(request, 'Not allowed to view this page')
    
    resp = HttpResponse(version.file_attachment.chunks(), content_type=version.file_mediatype)
    resp['Content-Disposition'] = disposition+'; filename=' + version.file_name
    resp['Content-Length'] = version.file_attachment.size
    return resp
    

@login_required
def page_history(request, course_slug, page_label):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    page = get_object_or_404(Page, offering=offering, label=page_label)
    member = _check_allowed(request, offering, page.can_write)
    # check that we have an allowed member of the course (and can continue)
    if not member:
        return ForbiddenResponse(request, "Not allowed to view this page's history")
    
    versions = PageVersion.objects.filter(page=page).order_by('-created_at')
    
    context = {'offering': offering, 'page': page, 'versions': versions}
    return render(request, 'pages/page_history.html', context)
    
@login_required
def page_version(request, course_slug, page_label, version_id):
    pass 
    

@login_required
def new_page(request, course_slug):
    return _edit_pagefile(request, course_slug, page_label=None, kind="page")

@login_required
def new_file(request, course_slug):
    return _edit_pagefile(request, course_slug, page_label=None, kind="file")

@login_required
def edit_page(request, course_slug, page_label):
    return _edit_pagefile(request, course_slug, page_label, kind=None)



def _edit_pagefile(request, course_slug, page_label, kind):
    """
    View to create and edit pages
    """
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    if page_label:
        page = get_object_or_404(Page, offering=offering, label=page_label)
        version = page.current_version()
        member = _check_allowed(request, offering, page.can_write)
    else:
        page = None
        version = None
        member = _check_allowed(request, offering, 'STAF')
    
    # make sure we're looking at the right "kind" (page/file)
    if not kind:
        kind = "file" if version.is_filepage() else "page"

    # get the form class we need
    if kind == "page":
        Form = EditPageForm
    else:
        Form = EditFileForm
    
    # check that we have an allowed member of the course (and can continue)
    if not member:
        return ForbiddenResponse(request, 'Not allowed to edit/create this '+kind+'.')
    if member.role == 'STUD':
        # students get the restricted version of the form
        Form = Form.restricted_form
    
    if request.method == 'POST':
        form = Form(instance=page, offering=offering, data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save(editor=member)
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description="Edited page \"%s\" in %s." % (form.instance.title, offering),
                  related_object=form.instance)
            l.save()
            if page:
                messages.success(request, "Edited "+kind+" \"%s\"." % (form.instance.title))
            else:
                messages.success(request, "Created "+kind+" \"%s\"." % (form.instance.title))
            
            return HttpResponseRedirect(reverse('pages.views.view_page', kwargs={'course_slug': course_slug, 'page_label': form.instance.label}))
    else:
        form = Form(instance=page, offering=offering)
        if 'label' in request.GET:
            label = request.GET['label']
            if label == 'Index':
                form.initial['title'] = offering.name()
            else:
                form.initial['title'] = label.title()
            form.initial['label'] = label

    context = {'offering': offering, 'page': page, 'form': form, 'kind': kind.title()}
    return render(request, 'pages/edit_page.html', context)




