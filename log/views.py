from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models import Q
from log.models import LogEntry
import shlex
from django.http import HttpResponse
import re
from courselib.auth import requires_global_role

@requires_global_role("SYSA")
def index(request):
    if request.method == 'POST':
        q = request.POST.get('q')
        q = q.encode('ascii','ignore')
        reg = request.POST.get('reg')
        keywords = []

        logs = LogEntry.objects.all().order_by('-datetime')
        if reg == 'on':
            try:
                pattern = re.compile(q, re.IGNORECASE)
            except:
                return HttpResponse("Please check your regex.")
            new_logs = []
            for l in logs:
                s = l.display()
                if re.search(pattern, s) != None:
                    new_logs.append(l)
            logs = new_logs
        else:
            try:
                keywords = shlex.split(q)
            except:
                return HttpResponse("Please check your input.")
            for k in keywords:
                new_logs = []
                for l in logs:
                    s = l.display()
                    if k.lower() in s.lower():
                        new_logs.append(l)
                logs = new_logs

        logs = logs[:500]
    else:
        keywords = ""
        logs = None
        reg = ""

    return render_to_response("log/index.html", \
            {"keywords":keywords, "logs":logs, "reg":reg}, \
            context_instance=RequestContext(request))

    return render_to_response("log/index.html", context_instance=RequestContext(request))
