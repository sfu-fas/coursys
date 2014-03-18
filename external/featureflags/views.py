from django.shortcuts import render
from django.conf import settings
from django.template.base import TemplateDoesNotExist

def service_unavailable(request, *args, **kwargs):
    template = settings.FEATUREFLAGS_DISABLED_TEMPLATE
    try:
        return render(request, template, status=503)
    except TemplateDoesNotExist:
        return render(request, 'featureflags/service_unavailable.html', status=503)
