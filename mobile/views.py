from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response

from dashboard.views import _get_memberships, _get_news_list, _get_roles

def index(request):
    userid = request.user.username
    memberships = _get_memberships(userid)
    news_list = _get_news_list(userid, 1)
    roles = _get_roles(userid)

    context = {'memberships': memberships ,'news_list': news_list, 'roles': roles}
    return render_to_response('mobile/dashboard.html',
        context, context_instance=RequestContext(request));

