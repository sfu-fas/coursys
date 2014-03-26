from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from pages.models import Page, PageVersion, MEMBER_ROLES, ACL_ROLES
from pages.forms import EditPageForm, EditFileForm, PageImportForm, SiteImportForm
from coredata.models import Member, CourseOffering
from log.models import LogEntry
from courselib.auth import NotFoundResponse, ForbiddenResponse, HttpError
from importer import HTMLWiki
import json, datetime


def _check_allowed(request, offering, acl_value, date=None):
    """
    Check to see if the person is allowed to do this Page action.

    Returns Member object if possible; True if non-member who is allowed, or None if not allowed.
    
    If a release date is given and is in the future, acl_value is tightened accordingly.
    """
    acl_value = Page.adjust_acl_release(acl_value, date)

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

def _forbidden_response(request, visible_to):
    """
    A nicer forbidden message that says why, and gently suggests that anonymous users log in.
    """
    error = 'Not allowed to view this page. It is visible only to %s in this course.' % (visible_to,)
    errormsg_template = '<strong>You are not currently logged in</strong>. You may be able to view this page if you <a href="%s">log in</a>'
    errormsg = None
    if not request.user.is_authenticated():
        url = conditional_escape(settings.LOGIN_URL + '?next=' + request.get_full_path())
        errormsg = mark_safe(errormsg_template % (url))

    return HttpError(request, status=403, title="Forbidden", error=error, errormsg=errormsg)


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
        member = _check_allowed(request, offering, offering.page_creators()) # users who can create pages
        can_create = bool(member)
        context = {'offering': offering, 'can_create': can_create, 'page_label': page_label}
        return render(request, 'pages/missing_page.html', context, status=404)
    else:
        page = pages[0]
    
    version = page.current_version()
    
    member = _check_allowed(request, offering, page.can_read, page.releasedate())
    # check that we have an allowed member of the course (and can continue)
    if not member:
        if _check_allowed(request, offering, page.can_read, None):
            # would be allowed without the date restriction: report that nicely
            context = {'offering': offering, 'page_label': page_label, 'releasedate': page.releasedate(),
                       'page_label': page.label}
            return render(request, 'pages/unreleased_page.html', context, status=403)

        return _forbidden_response(request, page.get_can_read_display())

    if request.user.is_authenticated():
        editor = _check_allowed(request, offering, page.can_write, page.editdate())
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
    
    member = _check_allowed(request, offering, page.can_read, page.releasedate())
    # check that we have an allowed member of the course (and can continue)
    if not member:
        return _forbidden_response(request, page.get_can_read_display())
    
    resp = HttpResponse(version.file_attachment.chunks(), content_type=version.file_mediatype)
    resp['Content-Disposition'] = disposition+'; filename="' + version.file_name + '"'
    resp['Content-Length'] = version.file_attachment.size
    return resp
    

@login_required
def page_history(request, course_slug, page_label):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    page = get_object_or_404(Page, offering=offering, label=page_label)
    member = _check_allowed(request, offering, page.can_write, page.editdate())
    # check that we have an allowed member of the course (and can continue)
    if not member:
        return _forbidden_response(request, page.get_can_write_display())
    
    versions = PageVersion.objects.filter(page=page).order_by('-created_at')
    
    context = {'offering': offering, 'page': page, 'versions': versions}
    return render(request, 'pages/page_history.html', context)
    

def page_version(request, course_slug, page_label, version_id):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    page = get_object_or_404(Page, offering=offering, label=page_label)
    member = _check_allowed(request, offering, page.can_write, page.editdate())
    # check that we have an allowed member of the course (and can continue)
    if not member:
        return _forbidden_response(request, page.get_can_write_display())
    
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


@transaction.atomic
def _edit_pagefile(request, course_slug, page_label, kind):
    """
    View to create and edit pages
    """
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    if page_label:
        page = get_object_or_404(Page, offering=offering, label=page_label)
        version = page.current_version()
        member = _check_allowed(request, offering, page.can_write, page.editdate())
    else:
        page = None
        version = None
        member = _check_allowed(request, offering, offering.page_creators()) # users who can create pages
    
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
    restricted = False
    if member.role == 'STUD':
        # students get the restricted version of the form
        Form = Form.restricted_form
        restricted = True
    
    if request.method == 'POST':
        form = Form(instance=page, offering=offering, data=request.POST, files=request.FILES)
        if form.is_valid():
            instance = form.save(editor=member)
            
            # clean up weirdness from restricted form
            if 'label' not in form.cleaned_data:
                # happens when student edits an existing page
                instance.label = page.label
            if 'can_write' not in form.cleaned_data:
                # happens only when students create a page
                instance.can_write = 'STUD'
            
            if not restricted and 'releasedate' in form.cleaned_data:
                instance.set_releasedate(form.cleaned_data['releasedate'])
            elif not restricted:
                instance.set_releasedate(None)

            if not restricted and 'editdate' in form.cleaned_data:
                instance.set_editdate(form.cleaned_data['editdate'])
            elif not restricted:
                instance.set_editdate(None)

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


def convert_content(request, course_slug, page_label=None):
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
    
    to = request.POST['to']
    data = request.POST['data']
    if to == 'html':
        # convert wikitext to HTML
        # temporarily change the current version to get the result (but don't save)
        if page_label:
            page = get_object_or_404(Page, offering=offering, label=page_label)
            pv = page.current_version()
        else:
            # create temporary Page for conversion during creation
            p = Page(offering=offering)
            pv = PageVersion(page=p)
        
        pv.wikitext = data
        pv.diff_from = None
        result = {'data': pv.html_contents()}
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        # convert HTML to wikitext
        converter = HTMLWiki([])
        try:
            wiki = converter.from_html(data)
        except converter.ParseError:
            wiki = ''
        result = {'data': wiki}
        return HttpResponse(json.dumps(result), content_type="application/json")


@login_required
@transaction.atomic
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
@transaction.atomic
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








from django.forms import ValidationError
from coredata.models import Person
from pages.models import ACL_DESC, WRITE_ACL_DESC
import base64
@transaction.atomic
def _pages_from_json(request, offering, data):
    try:
        data = data.decode('utf-8')
    except UnicodeDecodeError:
        raise ValidationError(u"Bad UTF-8 data in file.")
        
    try:
        data = json.loads(data)
    except ValueError as e:
        raise ValidationError(u'JSON decoding error.  Exception was: "' + str(e) + '"')
    
    if not isinstance(data, dict):
        raise ValidationError(u'Outer JSON data structure must be an object.')
    if 'userid' not in data or 'token' not in data:
        raise ValidationError(u'Outer JSON data object must contain keys "userid" and "token".')
    if 'pages' not in data:
        raise ValidationError(u'Outer JSON data object must contain keys "pages".')
    if not isinstance(data['pages'], list):
        raise ValidationError(u'Value for "pages" must be a list.')
    
    try:
        user = Person.objects.get(userid=data['userid'])
        member = Member.objects.exclude(role='DROP').get(person=user, offering=offering)
    except Person.DoesNotExist, Member.DoesNotExist:
        raise ValidationError(u'Person with that userid does not exist.')
    
    if 'pages-token' not in user.config or user.config['pages-token'] != data['token']:
        e = ValidationError(u'Could not validate authentication token.')
        e.status = 403
        raise e
    
    # if we get this far, the user is authenticated and we can start processing the pages...
    
    for i, pdata in enumerate(data['pages']):
        if not isinstance(pdata, dict):
            raise ValidationError(u'Page #%i entry structure must be an object.' % (i))
        if 'label' not in pdata:
            raise ValidationError(u'Page #%i entry does not have a "label".' % (i))
        
        # handle changes to the Page object
        pages = Page.objects.filter(offering=offering, label=pdata['label'])
        if pages:
            page = pages[0]
            old_ver = page.current_version()
        else:
            page = Page(offering=offering, label=pdata['label'])
            old_ver = None

        # check write permissions
        
        # mock the request object enough to satisfy _check_allowed()
        class FakeRequest(object): pass
        fake_request = FakeRequest()
        fake_request.user = FakeRequest()
        fake_request.user.username = user.userid
        if old_ver:
            m = _check_allowed(fake_request, offering, page.can_write, page.editdate())
        else:
            m = _check_allowed(fake_request, offering, offering.page_creators())
        if not m:
            raise ValidationError(u'You can\'t edit page #%i.' % (i))
        
        # handle Page attributes
        if 'can_read' in pdata:
            if type(pdata['can_read']) != unicode or pdata['can_read'] not in ACL_DESC:
                raise ValidationError(u'Page #%i "can_read" value must be one of %s.'
                                      % (i, ','.join(ACL_DESC.keys())))
            
            page.can_read = pdata['can_read']

        if 'can_write' in pdata:
            if type(pdata['can_write']) != unicode or pdata['can_write'] not in WRITE_ACL_DESC:
                raise ValidationError(u'Page #%i "can_write" value must be one of %s.'
                                      % (i, ','.join(WRITE_ACL_DESC.keys())))
            if m.role == 'STUD':
                raise ValidationError(u'Page #%i: students can\'t change can_write value.' % (i))
            page.can_write = pdata['can_write']
        
        if 'new_label' in pdata:
            if type(pdata['new_label']) != unicode:
                raise ValidationError(u'Page #%i "new_label" value must be a string.' % (i))
            if m.role == 'STUD':
                raise ValidationError(u'Page #%i: students can\'t change label value.' % (i))
            if Page.objects.filter(offering=offering, label=pdata['new_label']):
                raise ValidationError(u'Page #%i: there is already a page with that "new_label".' % (i))

            page.label = pdata['new_label']

        page.save()

        # handle PageVersion changes
        ver = PageVersion(page=page, editor=member)
        
        if 'title' in pdata:
            if type(pdata['title']) != unicode:
                raise ValidationError(u'Page #%i "title" value must be a string.' % (i))
            
            ver.title = pdata['title']
        elif old_ver:
            ver.title = old_ver.title
        else:
            raise ValidationError(u'Page #%i has no "title" for new page.' % (i))

        if 'comment' in pdata:
            if type(pdata['comment']) != unicode:
                raise ValidationError(u'Page #%i "comment" value must be a string.' % (i))
            
            ver.comment = pdata['comment']

        if 'use_math' in pdata:
            if type(pdata['use_math']) != bool:
                raise ValidationError(u'Page #%i "comment" value must be a boolean.' % (i))
            
            ver.set_math(pdata['use_math'])

        if 'wikitext-base64' in pdata:
            if type(pdata['wikitext-base64']) != unicode:
                raise ValidationError(u'Page #%i "wikitext-base64" value must be a string.' % (i))
            try:
                wikitext = base64.b64decode(pdata['wikitext-base64'])
            except TypeError:
                raise ValidationError(u'Page #%i "wikitext-base64" contains bad base BASE64 data.' % (i))
            
            ver.wikitext = wikitext
        elif 'wikitext' in pdata:
            if type(pdata['wikitext']) != unicode:
                raise ValidationError(u'Page #%i "wikitext" value must be a string.' % (i))
            
            ver.wikitext = pdata['wikitext']
        elif old_ver:
            ver.wikitext = old_ver.wikitext
        else:
            raise ValidationError(u'Page #%i has no wikitext for new page.' % (i))
        
        ver.save()
    
    return user


# testing like this:
# curl -i -X POST -H "Content-Type: application/json" -d @pages-import.json http://localhost:8000/2013su-cmpt-165-d1/pages/_push
@csrf_exempt
def api_import(request, course_slug):
    """
    API to allow automated Pages updates
    """
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    
    if request.method != 'POST':
        return HttpError(request, status=405, title="Method not allowed", error="This URL accepts only POST requests", errormsg=None, simple=True)
    if request.META['CONTENT_TYPE'] != 'application/json':
        return HttpError(request, status=415, title='Unsupported Media Type', error="Media type of request must be 'application/json'.", simple=True)
    
    data = request.read()
    try:
        user = _pages_from_json(request, offering, data)
        #LOG EVENT#
        l = LogEntry(userid=user.userid,
              description="API import of pages in %s." % (offering,),
              related_object=offering)
        l.save()

    except ValidationError as e:
        status = 400
        if hasattr(e, 'status'):
            status = e.status
        return HttpError(request, status=status, title='Bad request', error=e.messages[0], simple=True)

    return HttpError(request, status=200, title='Success', error='Page import successful.', simple=True)












