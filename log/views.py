from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models import Q
from log.models import LogEntry
import shlex
from django.http import HttpResponse

def index(request):
    if request.method == 'POST':
        q = request.POST.get('q')
        q = q.encode('ascii','ignore')
        keywords = []
        try:
            keywords = shlex.split(q)
        except:
            return HttpResponse("Please check your input.<hr>")
        
        print keywords
        list = LogEntry.objects.all().order_by('-datetime')
        for k in keywords:
            new_list = []
            for l in list:
                str = l.display()
                if k.lower() in str.lower():
                    new_list.append(l)
            list = new_list
#            list = list.filter(
##                Q(datetime__ctime__contains = k) |
#                Q(userid__contains = k) |
#                Q(description__contains = k) |
#                Q(comment__contains = q)).order_by('-datetime')
        return render_to_response("log/result.html", \
            {"keywords":keywords, "log_list":list}, \
            context_instance=RequestContext(request))
    else:
        return render_to_response("log/index.html", context_instance=RequestContext(request))
