from courselib.auth import requires_global_role, requires_role
from .models import Visa
from .forms import VisaForm, VisaAttachmentForm, VisaFilterForm
from django.shortcuts import render, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.http import StreamingHttpResponse
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from log.models import LogEntry
from datetime import datetime
from courselib.search import find_userid_or_emplid
from coredata.models import Person, Unit
import csv
from django.utils.html import conditional_escape as escape
from django_datatables_view.base_datatable_view import BaseDatatableView
from haystack.query import SearchQuerySet


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def list_all_visas(request, emplid=None):
    if 'tabledata' in request.GET:
        return VisaDataJson.as_view(emplid=emplid)(request)
    if emplid:
        person = Person.objects.get(find_userid_or_emplid(emplid))
    else:
        person = None
    units = Unit.sub_units(request.units)
    form = VisaFilterForm(units, person)
    context = {'person': person, 'form': form}
    return render(request, 'visas/view_visas.html', context)

def add_visa_display_class(visa):
    if visa.is_expired():
        return 'visaexpired'
    elif visa.is_almost_expired():
        return 'visaalmostexpired'
    elif visa.is_valid():
        return 'visavalid'
    else:
        return ""

class VisaDataJson(BaseDatatableView):
    model = Visa
    columns = ['person', 'emplid', 'unit', 'start_date', 'end_date', 'status', 'validity']
    order_columns = [
        ['person__last_name', 'person__first_name'],
        'person__emplid',
        'unit__label',
        'start_date',
        'end_date',
        'status'
    ]
    max_display_length = 500
    emplid = None

    def get_initial_queryset(self):
        qs = super(VisaDataJson, self).get_initial_queryset()
        qs = qs.select_related('unit')
        return qs

    def filter_queryset(self, qs):
        GET = self.request.GET
        
        emplid = self.emplid
        if emplid:
            person = Person.objects.get(find_userid_or_emplid(self.emplid))
            qs = qs.visible_given_user(person)
        
        qs = qs.visible_by_unit(Unit.sub_units(self.request.units))

        # search box
        srch = GET.get('sSearch', None)
        if srch:
            visa_qs = SearchQuerySet().models(Visa).filter(text__fuzzy=srch)[:500]
            visa_qs = [r for r in visa_qs if r is not None]
            if visa_qs:
                max_score = max(r.score for r in visa_qs)
                visa_pks = (r.pk for r in visa_qs if r.score > max_score/5)
                qs = qs.filter(id__in=visa_pks)
            else:
                qs = qs.none()

        start_date = GET.get('start_date', None)
        if start_date:
            qs = qs.filter(start_date__gte=start_date)

        hide_expired = GET.get('hide_expired', None)
        if hide_expired == "True":
            qs = qs.exclude(end_date__lt=datetime.today())
        
        type = GET.get('type', None)
        if type:
            qs = qs.filter(status=type)

        unit = GET.get('unit', None)
        if unit:
            unit = Unit.objects.get(label=unit)
            qs = qs.filter(unit=unit)

        return qs

    def render_column(self, visa, column):
        visaexpiry = add_visa_display_class(visa)
        if column == 'person':
            url = visa.get_absolute_url()
            name = visa.person.sortname()
            if visa.has_attachments():
                extra_string = '&nbsp; <i class="fa fa-paperclip" title="Attachment(s)"></i>'
            else:
                extra_string = ''
            return '<a href="%s">%s%s</a>' % (escape(url), escape(name), extra_string)
        elif column == 'unit':
            return visa.unit.label
        elif column == 'emplid':
            return visa.person.emplid
        elif column == 'validity':
            return str("<span class=" + visaexpiry + ">%s</span>" % visa.get_validity())

        return str(getattr(visa, column))

@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def new_visa(request, emplid=None):
    if request.method == 'POST':
        form = VisaForm(request, request.POST)
        if form.is_valid():
            visa = form.save(commit=False)
            visa.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Visa for %s was created.' % visa.person.name()
                                 )
            l = LogEntry(userid=request.user.username,
                         description="added visa: %s" % (visa),
                         related_object=visa
                         )
            l.save()

            return HttpResponseRedirect(reverse('visas:view_visa', kwargs={'visa_id': visa.id}))
    else:
        if emplid:
            person = Person.objects.get(find_userid_or_emplid(emplid))
            form = VisaForm(request, initial={'person': person})
        else:
            form = VisaForm(request)

    return render(request, 'visas/new_visa.html', {'form': form})


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def edit_visa(request, visa_id):
    visa = get_object_or_404(Visa, pk=visa_id, hidden=False)
    if request.method == 'POST':
        form = VisaForm(request, request.POST, instance=visa)
        if form.is_valid():
            visa = form.save(commit=False)
            visa.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Visa for %s was modified.' % visa.person.name()
                                 )
            l = LogEntry(userid=request.user.username,
                         description="Edited visa: %s" % (visa),
                         related_object=visa
                         )
            l.save()
            return HttpResponseRedirect(reverse('visas:view_visa', kwargs={'visa_id': visa.id}))
    else:
        # The initial value needs to be the person's emplid in the form.
        # Django defaults to the pk, which is not human readable.
        form = VisaForm(request, instance=visa, initial={'person': visa.person.emplid})

    return render(request, 'visas/edit_visa.html', {'form': form, 'visa_id': visa_id})


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def view_visa(request, visa_id):
    visa = get_object_or_404(Visa, pk=visa_id, hidden=False)
    return render(request, 'visas/view_visa.html', {'visa': visa})


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def delete_visa(request, visa_id):
    if request.method == 'POST':
        visa = get_object_or_404(Visa, pk=visa_id, hidden=False)
        messages.add_message(request,
                             messages.SUCCESS,
                            'Visa for %s was deleted.' % visa.person.name()
                             )
        l = LogEntry(userid=request.user.username,
                     description="Deleted visa: %s" % (visa),
                     related_object=visa
                     )
        l.save()

        visa.hide()
        visa.save()
    return HttpResponseRedirect(reverse('visas:list_all_visas'))


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def download_visas_csv(request):
    visas = Visa.objects.visible_by_unit(Unit.sub_units(request.units))
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="visas-%s.csv"' % datetime.now().strftime('%Y%m%d')
    writer = csv.writer(response)
    writer.writerow(['Person', 'Email', 'Unit', 'Start Date', 'End Date', 'Type', 'Validity'])
    for v in visas:
        person = v.person
        email = v.person.email()
        unit = v.unit.name
        start_date = v.start_date
        end_date = v.end_date
        visa_type = v.status
        validity = v.get_validity()
        writer.writerow([person, email, unit, start_date, end_date, visa_type, validity])

    return response

@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
@transaction.atomic
def new_attachment(request, visa_id):
    visa = get_object_or_404(Visa, pk=visa_id, hidden=False)
    editor = get_object_or_404(Person, userid=request.user.username)

    form = VisaAttachmentForm()
    context = {"visa": visa,
               "attachment_form": form}

    if request.method == "POST":
        form = VisaAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.visa = visa
            attachment.created_by = editor
            upfile = request.FILES['contents']
            filetype = upfile.content_type
            if upfile.charset:
                filetype += "; charset=" + upfile.charset
            attachment.mediatype = filetype
            attachment.save()
            messages.add_message(request, messages.SUCCESS, 'File attachment was added.')
            l = LogEntry(userid=request.user.username,
                     description="Added file attachment to visa: %s, %s" % (visa, attachment),
                     related_object=visa
                     )
            l.save()
            return HttpResponseRedirect(reverse('visas:view_visa', kwargs={'visa_id':visa.id}))
        else:
            context.update({"attachment_form": form})

    return render(request, 'visas/visa_document_attachment_form.html', context)

@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def view_attachment(request, visa_id, attach_slug):
    visa = get_object_or_404(Visa, pk=visa_id, hidden=False)
    attachment = get_object_or_404(visa.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def download_attachment(request, visa_id, attach_slug):
    visa = get_object_or_404(Visa, pk=visa_id, hidden=False)
    attachment = get_object_or_404(visa.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def delete_attachment(request, visa_id, attach_slug):
    visa = get_object_or_404(Visa, pk=visa_id, hidden=False)
    attachment = get_object_or_404(visa.attachments.all(), slug=attach_slug)
    attachment.hide()
    messages.add_message(request,
                         messages.SUCCESS,
                         'Attachment deleted.'
                         )
    l = LogEntry(userid=request.user.username, description="Hid file attachment %s" % attachment, related_object=visa)
    l.save()
    return HttpResponseRedirect(reverse('visas:view_visa', kwargs={'visa_id':visa.id}))
