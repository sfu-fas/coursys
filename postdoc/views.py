from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, StreamingHttpResponse
from django.contrib import messages
from courselib.auth import requires_role
from coredata.models import Person, Role
from courselib.search import find_userid_or_emplid
from grad.models import GradStudent
from log.models import LogEntry
from tacontracts.models import TAContract
from ta.models import TAContract as OldTAContract
from postdoc.forms import PostDocFundingSourceFormSet, PostDocForm, PostDocNoteForm, PostDocAdminAttachmentForm, PostDocDownloadForm, PostDocSupervisorFormSet
from postdoc.models import PostDoc, PostDocFundingSource
from visas.models import Visa
import csv
import datetime


@requires_role(['PDMA', 'PDOC'])
def post_doctoral_fellow(request: HttpRequest) -> HttpResponse:
    appointments = PostDoc.objects.filter(unit__in=request.units, deleted=False).select_related('person', 'unit').prefetch_related('supervisor_links__supervisor').order_by('-start_date', '-end_date')
    postdoc_admin = Role.objects_fresh.filter(role='PDMA', person__userid=request.user.username).exists()
    return render(request, 'postdoc/post_doctoral_fellow.html', {'appointments': appointments, 'postdoc_admin': postdoc_admin})


@requires_role(['PDMA', 'PDOC'])
def view_postdoc_appointment(request: HttpRequest, postdoc_slug: str) -> HttpResponse:
    appt = get_object_or_404(PostDoc.objects.select_related('person', 'unit').prefetch_related(Prefetch('funding_sources', queryset=PostDocFundingSource.objects.order_by('start_date', 'id'))), slug=postdoc_slug, unit__in=request.units, deleted=False)
    postdoc_admin = Role.objects_fresh.filter(role='PDMA', person__userid=request.user.username).exists()
    return render(request, 'postdoc/view_postdoc_appointment.html', {'appt': appt, 'postdoc_admin': postdoc_admin})


@requires_role('PDMA')
def new_postdoc_appointment(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = PostDocForm(request.POST, units=request.units)
        supervisor_formset = PostDocSupervisorFormSet(request.POST, prefix='supervisors')
        funding_formset = PostDocFundingSourceFormSet(request.POST, prefix='funding')
        if form.is_valid() and supervisor_formset.is_valid() and funding_formset.is_valid():
            editor = get_object_or_404(Person, userid=request.user.username)
            appt = form.save(commit=False)
            appt.last_updater = editor
            appt.save()
            supervisor_formset.instance = appt
            supervisor_formset.save()
            funding_formset.instance = appt
            funding_formset.save()
            l = LogEntry(userid=request.user.username,
                         description="New Post Doc Appointment %s." % appt,
                         related_object=appt)
            l.save()
            messages.success(request, 'New Post Doc Appointment Created for ' + str(appt.person))
            return HttpResponseRedirect(reverse('postdoc:view_postdoc_appointment', kwargs={'postdoc_slug': appt.slug}))
    else:
        form = PostDocForm(units=request.units)
        supervisor_formset = PostDocSupervisorFormSet(prefix='supervisors')
        funding_formset = PostDocFundingSourceFormSet(prefix='funding')

    return render(request, 'postdoc/new_postdoc_appointment.html', {'form': form, 'supervisor_formset': supervisor_formset, 'funding_formset': funding_formset})


@requires_role('PDMA')
def edit_postdoc_appointment(request: HttpRequest, postdoc_slug: str) -> HttpResponse:
    appt = get_object_or_404(PostDoc, slug=postdoc_slug, unit__in=request.units, deleted=False)
    if request.method == 'POST':
        form = PostDocForm(request.POST, instance=appt, units=request.units)
        supervisor_formset = PostDocSupervisorFormSet(request.POST, instance=appt, prefix='supervisors')
        funding_formset = PostDocFundingSourceFormSet(request.POST, instance=appt, prefix='funding')

        if form.is_valid() and supervisor_formset.is_valid() and funding_formset.is_valid():
            editor = get_object_or_404(Person, userid=request.user.username)
            appt = form.save(commit=False)
            appt.last_updater = editor
            appt.save()
            supervisor_formset.instance = appt
            supervisor_formset.save()
            funding_formset.instance = appt
            funding_formset.save()
            l = LogEntry(userid=request.user.username,
                description="Edited Post Doc Appointment %s." % appt,
                related_object=appt)
            l.save()
            messages.success(request, 'Edited Post Doc Appointment for ' + str(appt.person))
            return HttpResponseRedirect(reverse('postdoc:view_postdoc_appointment', kwargs={'postdoc_slug': appt.slug}))
    else:
        form = PostDocForm(instance=appt, units=request.units, initial={'person': appt.person.emplid})
        supervisor_formset = PostDocSupervisorFormSet(instance=appt, prefix='supervisors')
        funding_formset = PostDocFundingSourceFormSet(instance=appt, prefix='funding')

    return render(request, 'postdoc/new_postdoc_appointment.html', {'form': form, 'edit': True, 'supervisor_formset': supervisor_formset, 'funding_formset': funding_formset, 'appt': appt})

@requires_role(['PDMA', 'PDOC'])
def edit_postdoc_notes(request: HttpRequest, postdoc_slug: str) -> HttpResponse:
    appt = get_object_or_404(PostDoc, slug=postdoc_slug, unit__in=request.units, deleted=False)

    if request.method == 'POST':
        noteform = PostDocNoteForm(request.POST, instance=appt)
        if noteform.is_valid():
            appt.last_updater = get_object_or_404(Person, userid=request.user.username)
            noteform.save()
            l = LogEntry(userid=request.user.username, description="Edited Post Doc Appointment Notes for %s." % appt, related_object=appt)
            l.save()
            messages.success(request, 'Edited Notes for ' + str(appt.person))
            return HttpResponseRedirect(reverse('postdoc:view_postdoc_appointment', kwargs={'postdoc_slug': appt.slug}))
    else:
        noteform = PostDocNoteForm(instance=appt)

    return render(request, 'postdoc/edit_postdoc_notes.html', {'noteform': noteform, 'appt': appt})


@requires_role(['PDMA', 'PDOC'])
def new_admin_attachment(request: HttpRequest, postdoc_slug: str) -> HttpResponse:
    appt = get_object_or_404(PostDoc, slug=postdoc_slug, unit__in=request.units, deleted=False)
    editor = get_object_or_404(Person, userid=request.user.username)
    if request.method == 'POST':
        form = PostDocAdminAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.appt = appt
            attachment.created_by = editor
            upfile = request.FILES['contents']
            filetype = upfile.content_type
            if upfile.charset:
                filetype += '; charset=' + upfile.charset
            attachment.mediatype = filetype
            attachment.save()
            appt.last_updater = editor
            appt.save()
            l = LogEntry(userid=request.user.username, description="Added Admin Attachment for %s." % appt, related_object=appt)
            l.save()
            messages.success(request, 'Attachment added.')
            return HttpResponseRedirect(reverse('postdoc:view_postdoc_appointment', kwargs={'postdoc_slug': appt.slug}))
    else:
        form = PostDocAdminAttachmentForm()

    return render(request, 'postdoc/new_postdoc_attachment.html', {'appt': appt, 'attachment_form': form})


@requires_role(['PDMA', 'PDOC'])
def view_admin_attachment(request: HttpRequest, postdoc_slug: str, attach_slug: str) -> HttpResponse:
    appt = get_object_or_404(PostDoc, slug=postdoc_slug, unit__in=request.units, deleted=False)
    attachment = get_object_or_404(appt.attachments.visible(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    response = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    response['Content-Disposition'] = 'inline; filename="' + filename + '"'
    response['Content-Length'] = attachment.contents.size
    return response


@requires_role(['PDMA', 'PDOC'])
def download_admin_attachment(request: HttpRequest, postdoc_slug: str, attach_slug: str) -> HttpResponse:
    appt = get_object_or_404(PostDoc, slug=postdoc_slug, unit__in=request.units, deleted=False)
    attachment = get_object_or_404(appt.attachments.visible(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    response = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    response['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    response['Content-Length'] = attachment.contents.size
    return response


@requires_role('PDMA')
def delete_admin_attachment(request: HttpRequest, postdoc_slug: str, attach_slug: str) -> HttpResponse:
    appt = get_object_or_404(PostDoc, slug=postdoc_slug, unit__in=request.units, deleted=False)
    attachment = get_object_or_404(appt.attachments.visible(), slug=attach_slug)
    attachment.hide()
    appt.last_updater = get_object_or_404(Person, userid=request.user.username)
    appt.save()
    l = LogEntry(userid=request.user.username, description="Deleted Admin Attachment for %s." % appt, related_object=appt)
    l.save()
    messages.success(request, 'Attachment deleted.')
    return HttpResponseRedirect(reverse('postdoc:view_postdoc_appointment', kwargs={'postdoc_slug': appt.slug}))


@requires_role('PDMA')
def delete_postdoc_appointment(request: HttpRequest, postdoc_slug: str) -> HttpResponse:
    appt = get_object_or_404(PostDoc, slug=postdoc_slug, unit__in=request.units, deleted=False)
    appt.deleted = True
    appt.last_updater = get_object_or_404(Person, userid=request.user.username)
    appt.save()
    l = LogEntry(userid=request.user.username, description="Deleted Post Doc Appointment %s." % appt, related_object=appt)
    l.save()
    messages.success(request, 'Post Doc appointment deleted.')
    return HttpResponseRedirect(reverse('postdoc:post_doctoral_fellow'))


@requires_role(['PDMA', 'PDOC'])
def download_index(request: HttpRequest) -> HttpResponse:
    """
    Advanced download CSVs of Post Doc Appointments for admins
    """
    form = PostDocDownloadForm(request.POST or None)
    if request.method == 'POST':
        start_date = form.data['start_date']
        end_date = form.data['end_date']
        current = form.data['current']
        include_visa_status = form.data['include_visa_status']
    else:
        start_date = (datetime.date.today() - datetime.timedelta(days=1095)).strftime('%Y-%m-%d')
        end_date = datetime.date.today().strftime('%Y-%m-%d')
        current = False
        include_visa_status = True
    context = {'form': form, 'start_date': start_date, 'end_date': end_date, 'current': current, 'include_visa_status': include_visa_status}
    return render(request, 'postdoc/download_index.html', context)


@requires_role(['PDMA', 'PDOC'])
def download_admin(request: HttpRequest) -> HttpResponse:
    """
    Download CSVs of appointments and requests for admin
    """
    today = datetime.date.today()
    start_date = request.GET['start_date']
    end_date = request.GET['end_date']
    current = True if request.GET['current'] == 'True' else False
    include_visa_status = True if request.GET['include_visa_status'] == 'True' else False

    appts = PostDoc.objects.filter(unit__in=request.units, deleted=False).select_related('person', 'unit')

    if current:
        slack = 14
        appts = appts.filter(start_date__lte=today + datetime.timedelta(days=slack), end_date__gte=today - datetime.timedelta(days=slack))
    else:
        appts = appts.filter(start_date__gte=start_date, start_date__lte=end_date)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="postdocs-%s.csv"' % (datetime.datetime.now().strftime('%Y%m%d'))

    visa_columns = []
    if include_visa_status:
        visa_columns = ['Most Recent Visa Type', 'Most Recent Visa Expiry Date']

    writer = csv.writer(response)
    writer.writerow(['Hiring Department (Unit)', 'PDF Name', 'PDF SFU ID', 'PDF Email', 'Supervisor Names', 'Supervisor IDs', 'Supervisor Emails', 'Funding Source Unit(s)',
        'Funding Source Fund(s)', 'Funding Source Project(s)'] + visa_columns + ['Start Date', 'End Date', 'Type', 'Pay Amount', 'Payment Type'])

    for appt in appts:
        visa_status_values = []
        if include_visa_status:
            recent_visa = Visa.objects.visible().filter(person=appt.person, start_date__lte=today).order_by('-start_date').first()
            if recent_visa:
                visa_status_values = [recent_visa.status, recent_visa.start_date]
            else:
                visa_status_values = ['', '']
        
        pay_amount = ''
        payment_type = ''
        if appt.lump_sum_payment is not None:
            pay_amount = appt.lump_sum_payment
            payment_type = 'Lump Sum'
        elif appt.annual_salary_amount is not None:
            pay_amount = appt.annual_salary_amount
            payment_type = 'Annual Salary'

        # supervisors list
        links = appt.supervisor_links.select_related('supervisor').order_by('id')
        supervisors = [lnk.supervisor for lnk in links if lnk.supervisor]
        supervisor_names = '; '.join(p.sortname() for p in supervisors if p)
        supervisor_ids = '; '.join(str(p.emplid) for p in supervisors if p and p.emplid)
        supervisor_emails = '; '.join(p.email() for p in supervisors if p and p.email())

        # funding sources
        sources = list(appt.funding_sources.all().order_by('id'))
        funding_units = '; '.join(str(fs.unit) for fs in sources if fs.unit is not None)
        funding_funds = '; '.join(str(fs.fund) for fs in sources if fs.fund is not None)
        funding_projects = '; '.join((fs.project or '') for fs in sources)

        writer.writerow([appt.unit.label, appt.person.sortname(), appt.person.emplid, appt.person.email(), supervisor_names, supervisor_ids, supervisor_emails,
            funding_units, funding_funds, funding_projects] + visa_status_values + [appt.start_date, appt.end_date, appt.get_type_display(), pay_amount, payment_type])

    return response

@requires_role(['PDMA', 'PDOC'])
def appointee_appointments(request: HttpRequest, userid) -> HttpResponse:
    """
    View to see all RA Requests/Appointments where a specific person is an appointee.
    """
    person = get_object_or_404(Person, find_userid_or_emplid(userid))
    appointments = PostDoc.objects.filter(person=person, unit__in=request.units, deleted=False).select_related('person', 'unit').prefetch_related('supervisor_links__supervisor').order_by('-created_at')
    grads = GradStudent.objects.filter(person=person, program__unit__in=request.units)
    tacontracts = TAContract.objects.filter(person=person, status__in=['NEW', 'SGN']).count() + OldTAContract.objects.filter(application__person=person).count()
    context = {'appointments': appointments, 'person': person, 'grads': grads, 'tacontracts': tacontracts}
    return render(request, 'postdoc/search/appointee_appointments.html', context)

@requires_role(['PDMA', 'PDOC'])
def supervisor_appointments(request: HttpRequest, userid) -> HttpResponse:
    """
    View to see all RA Requests/Appointments where a specific person is a supervisor.
    """
    person = get_object_or_404(Person, find_userid_or_emplid(userid))
    appointments = PostDoc.objects.filter(supervisor_links__supervisor=person, unit__in=request.units, deleted=False).select_related('person', 'unit').prefetch_related('supervisor_links__supervisor').distinct().order_by('-created_at')
    context = {'appointments': appointments, 'person': person}
    return render(request, 'postdoc/search/supervisor_appointments.html', context)
