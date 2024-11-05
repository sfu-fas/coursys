from courselib.auth import requires_role
from django.shortcuts import render

@requires_role("GRAD")
def config(request):
    context = {}
    return render(request, 'grad/config.html', context)

@requires_role("GRAD")
def reports(request):
    context = {}
    return render(request, 'grad/reports.html', context)