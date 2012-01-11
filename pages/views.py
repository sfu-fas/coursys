from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from pages.models import Page, PageVersion, MEMBER_ROLES, ACL_ROLES
from pages.forms import EditPageForm
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
    return view_page(request, course_slug, 'index')

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

def view_page(request, course_slug, page_slug):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    pages = Page.objects.filter(offering=offering, slug=page_slug)
    if not pages:
        # missing page: do something more clever than the 404
        member = _check_allowed(request, offering, 'STAF')
        can_create = bool(member)
        context = {'offering': offering, 'can_create': can_create, 'page_slug': page_slug}
        return render(request, 'pages/missing_page.html', context)
    else:
        page = pages[0]
    
    current_version = page.current_version()
    
    member = _check_allowed(request, offering, page.can_read)
    # check that we have an allowed member of the course (and can continue)
    if not member:
        return ForbiddenResponse(request, 'Not allowed to view this page')
    
    if request.user.is_authenticated():
       editor = _check_allowed(request, offering, page.can_write)
       can_edit = bool(editor)
    else:
       can_edit = False
    
    is_index = page_slug=='index'
    if is_index:
        # canonical-ize the index URL
        url = reverse(index_page, kwargs={'course_slug': course_slug})
        if request.path != url:
            return HttpResponseRedirect(url)
    
    context = {'offering': offering, 'page': page, 'current_version': current_version,
               'can_edit': can_edit, 'is_index': is_index}
    return render(request, 'pages/view_page.html', context)


@login_required
def edit_page(request, course_slug, page_slug=None):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    if page_slug:
        page = get_object_or_404(Page, offering=offering, slug=page_slug)
        member = _check_allowed(request, offering, page.can_write)
    else:
        page = None
        member = _check_allowed(request, offering, 'STAF')

    # check that we have an allowed member of the course (and can continue)
    if not member:
        return ForbiddenResponse(request, 'Not allowed to edit/create this page.')
    
    if request.method == 'POST':
        form = EditPageForm(instance=page, offering=offering, data=request.POST)
        if form.is_valid():
            form.save(editor=member)
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description="Edited page \"%s\" in %s." % (form.instance.title, offering),
                  related_object=form.instance)
            l.save()
            if page:
                messages.success(request, "Edited page \"%s\"." % (form.instance.title))
            else:
                messages.success(request, "Created page \"%s\"." % (form.instance.title))
            
            return HttpResponseRedirect(reverse('pages.views.view_page', kwargs={'course_slug': course_slug, 'page_slug': form.instance.slug}))
    else:
        form = EditPageForm(instance=page, offering=offering)
        if 'slug' in request.GET:
            slug = request.GET['slug']
            if slug == 'index':
                form.initial['title'] = offering.name()
            else:
                form.initial['title'] = slug.title()
            form.initial['label'] = slug.title()

    context = {'offering': offering, 'page': page, 'form': form}
    return render(request, 'pages/edit_page.html', context)




