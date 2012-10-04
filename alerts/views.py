
# alerts-views

from models import Alert, AlertType, OPEN_STATUSES, CLOSED_STATUSES 
from django.views.decorators.csrf import csrf_exempt
from courselib.auth import requires_role, HttpResponseRedirect, \
    ForbiddenResponse
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.core.exceptions import ValidationError
import rest

@csrf_exempt
#@transaction.commit_manually
def rest_alerts(request):
    """
    View to create new alerts via RESTful POST (json)
    """
    if request.method != 'POST':
        resp = HttpResponse(content='Only POST requests allowed', status=405)
        resp['Allow'] = 'POST'
        return resp

    if request.META['CONTENT_TYPE'] != 'application/json' and not request.META['CONTENT_TYPE'].startswith('application/json;'):
        return HttpResponse(content='Contents must be JSON (application/json)', status=415)

    try:
        rest.new_alerts(request.raw_post_data)
    except UnicodeDecodeError:
        return HttpResponse(content='Bad UTF-8 encoded text', status=400)
    except ValueError:
        return HttpResponse(content='Bad JSON in request body', status=400)
    except ValidationError as e:
        #transaction.rollback()
        return HttpResponse(content=e.messages[0], status=422)

    #transaction.commit()
    return HttpResponse(status=200)

@requires_role('ADVS')
def view_alerts(request, resolved=False):
    """
    View reported alerts created via the API
    """
    types = AlertType.objects.filter(unit__in=request.units)
    if( resolved ):
        alerts = Alert.objects.filter(alerttype__in=types, status__in=CLOSED_STATUSES)
    else:
        alerts = Alert.objects.filter(alerttype__in=types, status__in=OPEN_STATUSES)
    return render(request, 'alerts/view_alerts.html', {'alerts': alerts, 'resolved':resolved})


@requires_role('ADVS')
def view_resolved_alerts(request):
    """
    View reported problems that have been resolved
    """
    return view_alerts(request, True) 


@requires_role('ADVS')
def edit_alert(request, alert_id):
    """
    View to view and edit a problem's status
    """
    problem = get_object_or_404(Alert, pk=prob_id, unit__in=request.units)
    from_page = request.GET.get('from', '')
    if not from_page in ('resolved', ''):
        userid = from_page
        try:
            from_page = Person.objects.get(userid=userid)
        except Person.DoesNotExist:
            from_page = ''
    if request.method == 'POST':
        form = ProblemStatusForm(request.POST, instance=problem)
        if form.is_valid():
            problem = form.save(commit=False)
            if problem.is_closed():
                problem.resolved_at = datetime.datetime.now()
            else:
                problem.resolved_at = None
            problem.save()
            messages.add_message(request, messages.SUCCESS, "Problem status successfully changed.")
            return HttpResponseRedirect(reverse('advisornotes.views.view_problems'))
    else:
        if problem.is_closed():
            form = ProblemStatusForm(instance=problem)
        else:
            form = ProblemStatusForm(instance=problem, initial={'resolved_until': problem.default_resolved_until()})
    return render(request, 'advisornotes/edit_problem.html', {'problem': problem, 'from_page': from_page, 'form': form})
