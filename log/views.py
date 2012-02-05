from django.shortcuts import render_to_response
from django.template import RequestContext
from log.models import LogEntry
from courselib.auth import requires_global_role
from courselib.search import get_query

@requires_global_role("SYSA")
def index(request):
    if request.method == 'POST':
        q = request.POST.get('q')
        query = get_query(q, ['userid', 'description', 'comment'])
        logs = LogEntry.objects.order_by('-datetime').filter(query)[:200]
    else:
        keywords = ""
        logs = None
        reg = ""

    return render_to_response("log/index.html", \
            {"logs": logs}, \
            context_instance=RequestContext(request))

