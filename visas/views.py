from courselib.auth import requires_global_role, requires_role
from .models import Visa
from .forms import VisaForm
from django.shortcuts import render, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib import messages
from log.models import LogEntry
from datetime import datetime
import unicodecsv as csv


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def list_all_visas(request):
    context = {'visa_list': Visa.objects.visible}
    return render(request, 'visas/view_visas.html', context)


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def new_visa(request):
    if request.method == 'POST':
        form = VisaForm(request.POST)
        if form.is_valid():
            visa = form.save(commit=False)
            visa.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Visa was created.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="added visa: %s" % (visa),
                         related_object=visa.person
                         )
            l.save()

            return HttpResponseRedirect(reverse('visas.views.list_all_visas'))
    else:
        form = VisaForm()

    return render(request, 'visas/new_visa.html', {'form': form})


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def edit_visa(request, visa_id):
    visa = get_object_or_404(Visa, pk=visa_id)
    if request.method == 'POST':
        form = VisaForm(request.POST, instance=visa)
        if form.is_valid():
            visa = form.save(commit=False)
            visa.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Visa was successfully modified.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="edited visa: %s" % (visa),
                         related_object=visa.person
                         )
            l.save()

            return HttpResponseRedirect(reverse('visas.views.list_all_visas'))
    else:
        # The initial value needs to be the person's emplid in the form.
        # Django defaults to the pk, which is not human readable.
        form = VisaForm(instance=visa, initial={'person': visa.person.emplid})

    return render(request, 'visas/edit_visa.html', {'form': form, 'visa_id': visa_id})


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def delete_visa(request, visa_id):
    visa = get_object_or_404(Visa, pk=visa_id)
    messages.success(request, 'Hid visa for %s' % (visa.person.name()))
    l = LogEntry(userid=request.user.username,
                 description="deleted visa: %s" % (visa),
                 related_object=visa.person
                 )
    l.save()

    visa.hide()
    visa.save()
    return HttpResponseRedirect(reverse(list_all_visas))


@requires_role(["TAAD", "GRAD", "ADMN", "GRPD"])
def download_visas_csv(request):
    visas = Visa.objects.visible()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="%s.csv"' % datetime.now().strftime('%Y%m%d')
    writer = csv.writer(response)
    writer.writerow(['Person', 'Start Date', 'End Date', 'Type', 'Validity'])
    for v in visas:
        person = v.person
        start_date = v.start_date
        end_date = v.end_date
        visa_type = v.status
        validity = v.get_validity()
        writer.writerow([person, start_date, end_date, visa_type, validity])

    return response