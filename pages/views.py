from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from pages.models import Page, PageVersion, MEMBER_ROLES, ACL_ROLES
from pages.forms import EditPageForm, EditFileForm, PageImportForm, SiteImportForm
from coredata.models import Member, CourseOffering
from log.models import LogEntry
from courselib.auth import NotFoundResponse, ForbiddenResponse
from importer import HTMLWiki
import json

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
    """ 
    Index page for a course's site: 'slug/' === 'slug/Index'
    """
    return view_page(request, course_slug, 'Index')

def all_pages(request, course_slug):
    """
    List of all pages (that this user can view) for this offering
    """
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    member = _check_allowed(request, offering, 'ALL')
    
    if member and member!=True:
        pages = Page.objects.filter(offering=offering, can_read__in=ACL_ROLES[member.role])
        can_create = member.role in MEMBER_ROLES[offering.page_creators()]
    else:
        pages = Page.objects.filter(offering=offering, can_read='ALL')
        can_create = False

    context = {'offering': offering, 'pages': pages, 'can_create': can_create, 'member': member}
    return render(request, 'pages/all_pages.html', context)

def view_page(request, course_slug, page_label):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    pages = Page.objects.filter(offering=offering, label=page_label)
    if not pages:
        # missing page: do something more clever than the standard 404
        member = _check_allowed(request, offering, offering.page_creators()) # users who can creat
        can_create = bool(member)
        context = {'offering': offering, 'can_create': can_create, 'page_label': page_label}
        return render(request, 'pages/missing_page.html', context, status=404)
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
    

def page_version(request, course_slug, page_label, version_id):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    page = get_object_or_404(Page, offering=offering, label=page_label)
    member = _check_allowed(request, offering, page.can_write)
    # check that we have an allowed member of the course (and can continue)
    if not member:
        return ForbiddenResponse(request, "Not allowed to view this page's history")
    
    version = get_object_or_404(PageVersion, page=page, id=version_id)
    
    messages.info(request, "This is an old version of this page.")
    context = {'offering': offering, 'page': page, 'version': version,
               'is_old': True}
    return render(request, 'pages/view_page.html', context)



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
        member = _check_allowed(request, offering, offering.page_creators()) # users who can create
    
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
            instance = form.save(editor=member)
            
            # clean up weirdness from restricted form
            if 'label' not in form.cleaned_data:
                # happens when student edits an existing page
                instance.label = page.label
                instance.save()
            if 'can_write' not in form.cleaned_data:
                # happens only when students create a page
                instance.can_write = 'STUD'
                instance.save()
            
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description="Edited page %s in %s." % (instance.label, offering),
                  related_object=instance)
            l.save()
            if page:
                messages.success(request, "Edited "+kind+" \"%s\"." % (instance.label))
            else:
                messages.success(request, "Created "+kind+" \"%s\"." % (instance.label))

            if not page and instance.label == 'Index' and not offering.url():
                # new Index page but no existing course URL: set as course web page
                url = settings.BASE_ABS_URL + instance.get_absolute_url()
                offering.set_url(url)
                offering.save()
                messages.info(request, "Set course URL to new Index page.")
            
            return HttpResponseRedirect(reverse('pages.views.view_page', kwargs={'course_slug': course_slug, 'page_label': instance.label}))
    else:
        form = Form(instance=page, offering=offering)
        if 'label' in request.GET:
            label = request.GET['label']
            if label == 'Index':
                form.initial['title'] = offering.name()
                form.fields['label'].help_text += u'\u2014the label "Index" indicates the front page for this course.'
            else:
                form.initial['title'] = label.title()
            form.initial['label'] = label

    context = {'offering': offering, 'page': page, 'form': form, 'kind': kind.title()}
    return render(request, 'pages/edit_page.html', context)


@csrf_exempt
def convert_content(request, course_slug, page_label):
    """
    Convert between wikicreole and HTML (AJAX called in editor when switching editing modes)
    """
    if request.method != 'POST':
        return ForbiddenResponse(request, 'POST only')
    if 'to' not in request.POST:
        return ForbiddenResponse(request, 'must send "to" language')
    if 'data' not in request.POST:
        return ForbiddenResponse(request, 'must sent source "data"')

    offering = get_object_or_404(CourseOffering, slug=course_slug)
    page = get_object_or_404(Page, offering=offering, label=page_label)
    
    to = request.POST['to']
    data = request.POST['data']
    if to == 'html':
        # convert wikitext to HTML
        # temporarily change the current version to get the result (but don't save)
        pv = page.current_version()
        pv.wikitext = data
        pv.diff_from = None
        result = {'data': pv.html_contents()}
        return HttpResponse(json.dumps(result), mimetype="application/json")
    else:
        # convert HTML to wikitext
        converter = HTMLWiki([])
        try:
            wiki = converter.from_html(data)
        except converter.ParseError:
            wiki = ''
        result = {'data': wiki}
        return HttpResponse(json.dumps(result), mimetype="application/json")


@login_required
def import_page(request, course_slug, page_label):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    page = get_object_or_404(Page, offering=offering, label=page_label)
    version = page.current_version()
    member = _check_allowed(request, offering, page.can_write)
    if not member:
        return ForbiddenResponse(request, 'Not allowed to edit/create this page.')
    
    if request.method == 'POST':
        form = PageImportForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            wiki = form.cleaned_data['file'] or form.cleaned_data['url']

            # create Page editing form for preview-before-save
            pageform = EditPageForm(instance=page, offering=offering)
            pageform.initial['wikitext'] = wiki
            
            # URL for submitting that form
            url = reverse(edit_page, kwargs={'course_slug': offering.slug, 'page_label': page.label})
            messages.warning(request, "Page has not yet been saved, but your HTML has been imported below.")            
            context = {'offering': offering, 'page': page, 'form': pageform, 'kind': 'Page', 'import': True, 'url': url}
            return render(request, 'pages/edit_page.html', context)
    else:
        form = PageImportForm()
    
    context = {'offering': offering, 'page': page, 'version': version, 'form': form}
    return render(request, 'pages/import_page.html', context)


@login_required
def import_site(request, course_slug):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    member = _check_allowed(request, offering, 'STAF') # only staff can import
    if not member:
        return ForbiddenResponse(request, 'Not allowed to edit/create pages.')
    
    if request.method == 'POST':
        form = SiteImportForm(offering=offering, editor=member, data=request.POST, files=request.FILES)
        if form.is_valid():
            pages, errors = form.cleaned_data['url']
            for label in pages:
                page, pv = pages[label]
                page.save()
                pv.page_id = page.id
                pv.save()
    else:
        form = SiteImportForm(offering=offering, editor=member)
    
    context = {'offering': offering, 'form': form}
    return render(request, 'pages/import_site.html', context)
