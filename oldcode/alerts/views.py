from .models import Alert, AlertType, AlertUpdate, AlertEmailTemplate
from .forms import EmailForm, ResolutionForm, AlertUpdateForm, EmailResolutionForm
from courselib.auth import requires_role, HttpResponseRedirect, \
    ForbiddenResponse

from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.contrib import messages
from log.models import LogEntry
from django.forms.utils import ErrorList
from django.template import Template, Context
from django.core.mail import send_mail
from . import rest
import datetime
import json

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

    errors = []
    try:
        errors = rest.new_alerts(request.body)
    except UnicodeDecodeError:
        return HttpResponse(content='Bad UTF-8 encoded text', status=400)
    except ValueError:
        return HttpResponse(content='Bad JSON in request body', status=400)

    if errors:
        return HttpResponse(content=json.dumps(errors, indent=4), status=422)

    #transaction.commit()
    return HttpResponse(status=200)

@requires_role('ADVS')
def view_alert_types(request):
    """
    View reported alerts created via the API
    """
    types = AlertType.objects.filter(unit__in=request.units, hidden=False)
    for alert_type in types:
        alert_type.num_alerts = Alert.objects.filter(alerttype=alert_type, resolved=False, hidden=False).count() 

    return render(request, 'alerts/view_alert_types.html', {'alert_types': types })

def regularize_keys( alert, most_recent_alert ):
    """ As it turns out, alerts may not have the same key/value pairs as the most recent alert. """
    for key, value in most_recent_alert.details.items():
        if key not in alert.details:
            alert.details[key] = ""

    delete_keys = []
    for key, value in alert.details.items():
        if key not in most_recent_alert.details:
            delete_keys.append(key)

    for key in delete_keys:
        del alert.details[key]


@requires_role('ADVS')
def view_alerts(request, alert_type, option="UNRESOLVED"):
    """
    View reported alerts created via the API
    """
    alert_type = get_object_or_404(AlertType, slug=alert_type, unit__in=request.units)
    
    all_alerts = Alert.objects.filter( alerttype=alert_type, hidden=False )
    try:
        most_recent_alert = all_alerts.latest('created_at');
    except Alert.DoesNotExist:
        most_recent_alert = {}

    [ regularize_keys( alert, most_recent_alert ) for alert in all_alerts ]

    resolved_flag = option == "RESOLVED"
    unresolved_flag = option == "UNRESOLVED"
    all_flag = option == "ALL"

    bulk_counter = 0
    resolved_alerts = all_alerts.filter( resolved=True) 

    # only show Alerts that are unresolved and won't be automatically resolved. 
    unresolved_alerts = all_alerts.filter( resolved=False)
    
    alert_emails = AlertEmailTemplate.objects.filter( alerttype=alert_type, hidden=False ).order_by('threshold')
    alert_email_dict = dict( [ (key,[]) for key in alert_emails ] ) 

    unresolved_alerts_filtered= []   
 
    for alert in unresolved_alerts:
        number_of_warnings_sent = alert.alertupdate_set.filter( update_type='EMAI' ).count() 
        alert_will_be_automatically_handled = False
        for email in alert_emails:
            if number_of_warnings_sent < email.threshold:
                alert_email_dict[email].append( alert )
                alert_will_be_automatically_handled = True
                break
        if not alert_will_be_automatically_handled:
            unresolved_alerts_filtered.append( alert ) 
        else: 
            bulk_counter += 1

    if unresolved_flag:
        alerts = unresolved_alerts_filtered
    elif resolved_flag:
        alerts = resolved_alerts
    else:
        alerts = all_alerts

    return render(request, 'alerts/view_alerts.html', { 'alerts': alerts,
                                                        'resolved': resolved_flag,
                                                        'unresolved': unresolved_flag,
                                                        'all': all_flag,
                                                        'bulk_counter': bulk_counter,
                                                        'most_recent_alert': most_recent_alert,
                                                        'alert_type':alert_type})

@requires_role('ADVS')
def view_all_alerts(request, alert_type):
    return view_alerts(request, alert_type, "ALL") 


@requires_role('ADVS')
def view_resolved_alerts(request, alert_type):
    return view_alerts(request, alert_type, "RESOLVED") 

@requires_role('ADVS')
def view_automation(request, alert_type):
    alert_type = get_object_or_404(AlertType, slug=alert_type, unit__in=request.units)
        
    unresolved_alerts = Alert.objects.filter( alerttype=alert_type, resolved=False, hidden=False)

    try:
        most_recent_alert = unresolved_alerts.latest('created_at');
    except Alert.DoesNotExist:
        most_recent_alert = {}
    
    [ regularize_keys( alert, most_recent_alert ) for alert in unresolved_alerts ]
    
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
                                                            'alert_automations': alert_automations,
                                                            'most_recent_alert': most_recent_alert}) 

@requires_role('ADVS')
def new_automation(request, alert_type):
    alert_type = get_object_or_404(AlertType, slug=alert_type, unit__in=request.units)

    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            if AlertEmailTemplate.objects.filter(alerttype=alert_type, hidden=False, threshold=form.cleaned_data['threshold']).count() > 0:
                errors = form._errors.setdefault("threshold", ErrorList())
                errors.append('An e-mail with this threshold already exists.' )
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
        ("person.first_name", "The first name of the student."),
        ("person.last_name", "The last name of the student."),
        ("person.middle_name", "The middle name of the student."),
        ("person.emplid", "The student's emplid."),
        ("person.email", "The student's email."),
        ("person.title", "The student's title."),
        ("description","The description of the alert.")
    ]
    
    for k, v in sample_alert.details.items():
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

def build_context( alert ):
    email_context = {
        'person':{
        'name':alert.person.name(),
        'first_name':alert.person.first_name,
        'middle_name':alert.person.middle_name,
        'last_name':alert.person.last_name,
        'emplid':alert.person.emplid,
        'email':alert.person.email(),
        'title':alert.person.title,
        },
        'description':alert.description
    }
    return email_context
    

@requires_role('ADVS')
def view_email_preview(request, alert_type, alert_id, automation_id):
    alert_email = get_object_or_404(AlertEmailTemplate, id=automation_id)
    alert_type = get_object_or_404(AlertType, slug=alert_type, unit__in=request.units)
    alert = get_object_or_404(Alert, pk=alert_id, alerttype__unit__in=request.units)

    t = Template( alert_email.content )

    email_context = build_context( alert )    
    email_context['details'] = {}
    for k, v in alert.details.items():
        email_context['details'][k] = str(v)

    rendered_text = t.render( Context(email_context) ) 
    
    return render(request, 'alerts/view_email_preview.html', { 'alert_type':alert_type, 
                                                                'alert':alert, 
                                                                'alert_email':alert_email, 
                                                                'rendered_text':rendered_text })

@requires_role('ADVS')
def view_alert( request, alert_type, alert_id ):
    """
    View an alert
    """
    alert = get_object_or_404(Alert, pk=alert_id, alerttype__unit__in=request.units)
    alert_updates = AlertUpdate.objects.filter(alert=alert).order_by('-created_at')

    return render(request, 'alerts/view_alert.html', {'alert': alert, 'alert_updates': alert_updates })

@requires_role('ADVS')
def hide_alert( request, alert_type, alert_id ):
    alert = get_object_or_404(Alert, pk=alert_id, alerttype__unit__in=request.units)
    alert.hidden = True
    alert.save()
    messages.success(request, "Deleted alert %s." % str(alert) )
    return HttpResponseRedirect(reverse('alerts.views.view_resolved_alerts', kwargs={'alert_type':alert_type}))

@requires_role('ADVS')
def resolve_alert( request, alert_type, alert_id ):
    """
    Resolve an alert
    """
    alert = get_object_or_404(Alert, id=alert_id, alerttype__unit__in=request.units)
    
    if request.method == 'POST':
        form = ResolutionForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.alert = alert
            f.update_type = "RESO"
            f.save()
            messages.success(request, "Resolved alert %s." % str(alert) )
            l = LogEntry(userid=request.user.username,
                  description="Resolved alert %s." % str(alert),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse('alerts.views.view_alert', kwargs={'alert_type':alert_type, 'alert_id':alert_id}))
    else:
        form = ResolutionForm(initial={'resolved_until': datetime.date.today()})
    
    return render(request, 'alerts/resolve_alert.html', { 'alert_type':alert.alerttype, 
                                                          'alert':alert,
                                                          'form': form, 
                                                          'resolve_reopen_or_comment_on': 'Resolve'})

@requires_role('ADVS')
def reopen_or_comment_alert( request, alert_type, alert_id, update_code, wording):
    alert = get_object_or_404(Alert, id=alert_id, alerttype__unit__in=request.units)
    
    if request.method == 'POST':
        form = AlertUpdateForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.alert = alert
            f.update_type = update_code
            f.save()
            messages.success(request, "Updated alert %s." % str(alert) )
            l = LogEntry(userid=request.user.username,
                  description="Updated alert %s." % str(alert),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse('alerts.views.view_alert', kwargs={'alert_type':alert_type, 'alert_id':alert_id}))
    else:
        form = AlertUpdateForm()
    
    return render(request, 'alerts/resolve_alert.html', { 'alert_type':alert.alerttype, 
                                                          'alert':alert,
                                                          'form': form,
                                                          'resolve_reopen_or_comment_on': wording})

@requires_role('ADVS')
def reopen_alert( request, alert_type, alert_id ):
    """
    Reopen an alert
    """
    return reopen_or_comment_alert( request, alert_type, alert_id, "REOP", "Reopen" )

@requires_role('ADVS')
def comment_alert( request, alert_type, alert_id ):
    """
    Comment on an alert
    """
    return reopen_or_comment_alert( request, alert_type, alert_id, "COMM", "Comment on" )

@requires_role('ADVS')
def email_alert( request, alert_type, alert_id ):
    alert = get_object_or_404(Alert, id=alert_id, alerttype__unit__in=request.units)
    
    if request.method == 'POST':
        form = EmailResolutionForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.alert = alert
            f.update_type = "EMAI"
            f.save()
            messages.success(request, "Emailed student and resolved alert %s." % str(alert) )
            
            l = LogEntry(userid=request.user.username,
                  description="Resolved alert %s." % str(alert),
                  related_object=form.instance)
            l.save()            
            
            send_mail( form.cleaned_data['subject'], f.comments, form.cleaned_data['from_email'], [form.cleaned_data['to_email']] )
            return HttpResponseRedirect(reverse('alerts.views.view_alert', kwargs={'alert_type':alert_type, 'alert_id':alert_id}))
    else:
        form = EmailResolutionForm(initial={'resolved_until': datetime.date.today(), 'to_email': alert.person.email(), 'from_email': request.user.email})
    
    return render(request, 'alerts/email_alert.html', { 'alert_type':alert.alerttype, 
                                                          'alert':alert,
                                                          'form': form })

@requires_role('ADVS')
def send_emails( request, alert_type ):
    """
    Send all e-mails. 
    """

    alert_emails = AlertEmailTemplate.objects.all().order_by('threshold')
        
    unresolved_alerts = Alert.objects.filter( alerttype__slug=alert_type, resolved=False, hidden=False )
    
    alert_emails = AlertEmailTemplate.objects.filter( hidden=False ).order_by('threshold')
    alert_email_dict = dict( [ (key,[]) for key in alert_emails ] ) 

    for alert in unresolved_alerts:
        number_of_warnings_sent = alert.alertupdate_set.filter( update_type='EMAI' ).count() 
        for email in alert_emails:
            if number_of_warnings_sent < email.threshold:
                alert_email_dict[email].append( alert )
                break

    alert_automations = []
    for email in alert_emails:
        for alert in alert_email_dict[email]:
            email_context = build_context( alert )    
            t = Template( email.content )

            email_context = build_context( alert )    
            email_context['details'] = {}
            for k, v in alert.details.items():
                email_context['details'][k] = str(v)

            rendered_text = t.render( Context(email_context) ) 
            # TODO Right here: this should DEFINITELY be a celery task. 
            send_mail( email.subject, rendered_text, "noreply@courses.cs.sfu.ca", [alert.person.email()], fail_silently=True )
            update = AlertUpdate( alert=alert, update_type="EMAI", comments=rendered_text )
            update.save()

    return HttpResponseRedirect(reverse('alerts.views.view_alert_types'))
