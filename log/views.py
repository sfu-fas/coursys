from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models import Q
from log.models import LogEntry
import shlex
from django.http import HttpResponse
import re
from courselib.auth import requires_role

@requires_role("SYSA")
def index(request):
    if request.method == 'POST':
        q = request.POST.get('q')
        q = q.encode('ascii','ignore')
        reg = request.POST.get('reg')
        keywords = []

        list = LogEntry.objects.all().order_by('-datetime')
        if reg == 'on':
            try:
                pattern = re.compile(q, re.IGNORECASE)
            except:
                return HttpResponse("Please check your regex.<hr>")
            new_list = []
            for l in list:
                str = l.display()
                if re.search(pattern, str) != None:
                    new_list.append(l)
            list = new_list
        else:
            try:
                keywords = shlex.split(q)
            except:
                return HttpResponse("Please check your input.<hr>")
            for k in keywords:
                new_list = []
                for l in list:
                    str = l.display()
                    if k.lower() in str.lower():
                        new_list.append(l)
                list = new_list

        return render_to_response("log/result.html", \
            {"keywords":keywords, "log_list":list, "reg":reg}, \
            context_instance=RequestContext(request))
    else:
        return render_to_response("log/index.html", context_instance=RequestContext(request))
