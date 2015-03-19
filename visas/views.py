from courselib.auth import requires_global_role
from .models import Visa
from .forms import VisaForm
from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages


@requires_global_role("SYSA")
def list_all_visas(request):
    context = {'visa_list': Visa.objects.order_by('start_date')}
    return render(request, 'visas/view_visas.html', context)


@requires_global_role("SYSA")
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

            return HttpResponseRedirect(reverse('visas.views.list_all_visas'))
    else:
        form = VisaForm()

    return render(request, 'visas/new_visa.html', {'form': form})

@requires_global_role("SYSA")
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

            return HttpResponseRedirect(reverse('visas.views.list_all_visas'))
    else:
        form = VisaForm(instance=visa)

    return render(request, 'visas/edit_visa.html', {'form': form, 'visa_id': visa_id})


    



