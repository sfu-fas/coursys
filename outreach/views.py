from courselib.auth import requires_role
from django.shortcuts import render, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib import messages
from log.models import LogEntry
from datetime import datetime


@requires_role('OUTR')
def index(request):
    pass
