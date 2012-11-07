
from models import Alert, AlertType, AlertUpdate, AlertEmailTemplate
from forms import EmailForm 
from django.views.decorators.csrf import csrf_exempt
from courselib.auth import requires_role, HttpResponseRedirect, \
    ForbiddenResponse
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.contrib import messages
from log.models import LogEntry
from django.forms.util import ErrorList
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
def view_alert_types(request):
    """
    View reported alerts created via the API
    """
    types = AlertType.objects.filter(unit__in=request.units, hidden=False)
    for alert_type in types:
        alert_type.num_alerts = Alert.objects.filter(alerttype=alert_type, resolved=False).count() 

    return render(request, 'alerts/view_alert_types.html', {'alert_types': types })

@requires_role('ADVS')
def view_alerts(request, alert_type, resolved=False):
    """
    View reported alerts created via the API
    """
    alert_type = get_object_or_404(AlertType, slug=alert_type, unit__in=request.units)
    
    all_alerts = Alert.objects.filter( alerttype=alert_type, hidden=False )

    if resolved:
        alerts = all_alerts.filter( resolved=True) 
    else:
        # only show Alerts that are unresolved and won't be automatically resolved. 
        unresolved_alerts = all_alerts.filter( resolved=False)
        
        alert_emails = AlertEmailTemplate.objects.filter( alerttype=alert_type, hidden=False ).order_by('threshold')
        alert_email_dict = dict( [ (key,[]) for key in alert_emails ] ) 

        alerts= []   
     
        for alert in unresolved_alerts:
            number_of_warnings_sent = alert.alertupdate_set.filter( update_type='EMAI' ).count() 
            alert_will_be_automatically_handled = False
            for email in alert_emails:
                if number_of_warnings_sent < email.threshold:
                    alert_email_dict[email].append( alert )
                    alert_will_be_automatically_handled = True
                    break
            if not alert_will_be_automatically_handled:
                alerts.append( alert ) 

    return render(request, 'alerts/view_alerts.html', { 'alerts': alerts,
                                                        'resolved': resolved,
                                                        'alert_type':alert_type})

@requires_role('ADVS')
def view_automation(request, alert_type):
    alert_type = get_object_or_404(AlertType, slug=alert_type, unit__in=request.units)
    alert_emails = AlertEmailTemplate.objects.filter( alerttype=alert_type ).order_by('threshold')
        
    unresolved_alerts = Alert.objects.filter( alerttype=alert_type, resolved=False )
    
    alert_emails = AlertEmailTemplate.objects.filter( alerttype=alert_type, hidden=False ).order_by('threshold')
    alert_email_dict = dict( [ (key,[]) for key in alert_emails ] ) 

    for alert in unresolved_alerts:
        number_of_warnings_sent = alert.alertupdate_set.filter( update_type='EMAI' ).count() 
        for email in alert_emails:
            if number_of_warnings_sent < email.threshold:
                alert_email_dict[email].append( alert )
                break

    alert_automations = []

    first = True
    last_warning = 0
    suffixes = ["th", "st", "nd", "rd"] + ["th"] * 16
    suffixes = suffixes + suffixes * 6

    for email in alert_emails:
        if first:
            plural = "s" if email.threshold >= 2 else ""
            title = "First " + str( email.threshold ) + " Warning" + plural
            first = False
        else:
            next_warning = last_warning + 1
            if email.threshold - next_warning >= 1:
                title = "Warnings " + str(next_warning) + "-" + str(email.threshold)
            else:
                title = str(email.threshold) + suffixes[email.threshold % 100] + " Warning"

        alert_automations.append( (title, email, alert_email_dict[email]) )
        last_warning = email.threshold

    return render(request, 'alerts/view_automation.html', { 'alert_type': alert_type,
                                                            'alert_automations': alert_automations }) 

@requires_role('ADVS')
def new_automation(request, alert_type):
    alert_type = get_object_or_404(AlertType, slug=alert_type, unit__in=request.units)

    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            if AlertEmailTemplate.objects.filter(alerttype=alert_type, hidden=False, threshold=form.cleaned_data['threshold']).count() > 0:
                errors = form._errors.setdefault("threshold", ErrorList())
                errors.append(u'An e-mail with this threshold already exists.' )
            else:
                f = form.save(commit=False)
                f.alerttype = alert_type
                f.created_by = request.user.username            
                f.save()
                messages.success(request, "Created new automated email for %s." % alert_type.code)
                l = LogEntry(userid=request.user.username,
                      description="Created new automated email %s." % alert_type.code,
                      related_object=form.instance)
                l.save()            
                return HttpResponseRedirect(reverse('alerts.views.view_automation', kwargs={'alert_type':alert_type.slug}))
    else:
        form = EmailForm()

    sample_alert = Alert.objects.filter(alerttype=alert_type, hidden=False)[0]


    email_tags = [
        ("person.name","The name of the student that has triggered the alert"),
        ("description","The description of the alert.")
    ]
    
    for k, v in sample_alert.details.iteritems():
        email_tags.append( ("details."+k, "For example, (" + str(v) + ")") )
    
    return render(request, 'alerts/new_automation.html', { 'alert_type':alert_type, 'form': form, 'email_tags':email_tags })

@requires_role('ADVS')
def delete_automation( request, alert_type, automation_id ):
    auto= get_object_or_404(AlertEmailTemplate, id=automation_id)
    auto.hidden = True
    auto.save()
    messages.success(request, "Removed automation")
    l = LogEntry(userid=request.user.username,
          description="Removed automation.",
          related_object=auto)
    l.save()              
    
    return HttpResponseRedirect(reverse('alerts.views.view_automation', kwargs={'alert_type': alert_type}))

@requires_role('ADVS')
def view_resolved_alerts(request, alert_type):
    """
    View reported problems that have been resolved
    """
    return view_alerts(request, alert_type, True) 

@requires_role('ADVS')
def view_alert( request, alert_type, alert_id ):
    """
    View an alert
    """
    alert = get_object_or_404(Alert, pk=alert_id, alerttype__unit__in=request.units)
    alert_updates = AlertUpdate.objects.filter(alert=alert).order_by('-created_at')

    return render(request, 'alerts/view_alert.html', {'alert': alert, 'alert_updates': alert_updates })
