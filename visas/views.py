from courselib.auth import requires_global_role, requires_role
from .models import Visa
from .forms import VisaForm, VisaAttachmentForm
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


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def list_all_visas(request, emplid=None):
    if emplid:
        person = Person.objects.get(find_userid_or_emplid(emplid))
        visa_list = Visa.objects.visible_given_user(person)
    else:
        person = None
        visa_list = Visa.objects.visible_by_unit(Unit.sub_units(request.units))
    context = {'visa_list': visa_list, 'person': person}
    return render(request, 'visas/view_visas.html', context)


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def new_visa(request, emplid=None):
    if request.method == 'POST':
        form = VisaForm(request, request.POST)
        if form.is_valid():
            visa = form.save(commit=False)
            visa.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Visa was created.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="added visa: %s" % (visa),
                         related_object=visa.person
                         )
            l.save()

            return HttpResponseRedirect(reverse('visas:list_all_visas'))
    else:
        if emplid:
            person = Person.objects.get(find_userid_or_emplid(emplid))
            form = VisaForm(request, initial={'person': person})
        else:
            form = VisaForm(request)

    return render(request, 'visas/new_visa.html', {'form': form})


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def edit_visa(request, visa_id):
    visa = get_object_or_404(Visa, pk=visa_id)
    if request.method == 'POST':
        form = VisaForm(request, request.POST, instance=visa)
        if form.is_valid():
            visa = form.save(commit=False)
            visa.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Visa was successfully modified.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="edited visa: %s" % (visa),
                         related_object=visa.person
                         )
            l.save()

            return HttpResponseRedirect(reverse('visas:list_all_visas'))
    else:
        # The initial value needs to be the person's emplid in the form.
        # Django defaults to the pk, which is not human readable.
        form = VisaForm(request, instance=visa, initial={'person': visa.person.emplid})

    return render(request, 'visas/edit_visa.html', {'form': form, 'visa_id': visa_id})


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def view_visa(request, visa_id):
    visa = get_object_or_404(Visa, pk=visa_id)
    return render(request, 'visas/view_visa.html', {'visa': visa})


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def delete_visa(request, visa_id):
    if request.method == 'POST':
        visa = get_object_or_404(Visa, pk=visa_id)
        messages.success(request, 'Hid visa for %s' % (visa.person.name()))
        l = LogEntry(userid=request.user.username,
                     description="deleted visa: %s" % (visa),
                     related_object=visa.person
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
    writer.writerow(['Person', 'Unit', 'Start Date', 'End Date', 'Type', 'Validity'])
    for v in visas:
        person = v.person
        unit = v.unit.name
        start_date = v.start_date
        end_date = v.end_date
        visa_type = v.status
        validity = v.get_validity()
        writer.writerow([person, unit, start_date, end_date, visa_type, validity])

    return response

@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
@transaction.atomic
def new_attachment(request, visa_id):
    visa = get_object_or_404(Visa, pk=visa_id)
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
            return HttpResponseRedirect(reverse('visas:view_visa', kwargs={'visa_id':visa.id}))
        else:
            context.update({"attachment_form": form})

    return render(request, 'visas/visa_document_attachment_form.html', context)

@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def view_attachment(request, visa_id, attach_slug):
    visa = get_object_or_404(Visa, pk=visa_id)
    attachment = get_object_or_404(visa.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def download_attachment(request, visa_id, attach_slug):
    visa = get_object_or_404(Visa, pk=visa_id)
    attachment = get_object_or_404(visa.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def delete_attachment(request, visa_id, attach_slug):
    visa = get_object_or_404(Visa, pk=visa_id)
    attachment = get_object_or_404(visa.attachments.all(), slug=attach_slug)
    attachment.hide()
    messages.add_message(request,
                         messages.SUCCESS,
                         'Attachment deleted.'
                         )
    l = LogEntry(userid=request.user.username, description="Hid attachment %s" % attachment, related_object=attachment)
    l.save()
    return HttpResponseRedirect(reverse('visas:view_visa', kwargs={'visa_id':visa.id}))
