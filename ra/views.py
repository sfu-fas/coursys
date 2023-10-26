from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse, StreamingHttpResponse
from django.contrib import messages
from django.db.models import Q
from django.utils.html import conditional_escape as escape
from ra.models import RAAppointment, RARequest, Project, Account, SemesterConfig, Program
from ra.forms import RAForm, RASearchForm, AccountForm, ProjectForm, RALetterForm, RABrowseForm, SemesterConfigForm, \
    LetterSelectForm, RAAppointmentAttachmentForm, ProgramForm, RARequestAdminForm, RARequestNoteForm, RARequestAdminAttachmentForm, \
    RARequestPAFForm, RARequestLetterForm, RARequestResearchAssistantForm, RARequestGraduateResearchAssistantForm, RARequestNonContinuingForm, \
    RARequestFundingSourceForm, RARequestSupportingForm, RARequestDatesForm, RARequestIntroForm, RARequestAdminPAFForm, RARequestScienceAliveForm, \
    CS_CONTACT, ENSC_CONTACT, SEE_CONTACT, MSE_CONTACT, FAS_CONTACT, PD_CONTACT, URA_CONTACT, DEANS_CONTACT, AppointeeSearchForm, SupervisorSearchForm
from grad.forms import possible_supervisors
from coredata.models import Person, Role, Semester, Unit
from coredata.queries import more_personal_info, SIMSProblem
from courselib.auth import requires_role, has_role, ForbiddenResponse, user_passes_test
from courselib.search import find_userid_or_emplid, get_query
from grad.models import GradStudent, Scholarship
from visas.models import Visa
from log.models import LogEntry
from dashboard.letters import ra_form, ra_paf, ra_science_alive, FASOfficialLetter, OfficialLetter, LetterContents
from django import forms
from django.db import transaction
from django.http import HttpResponse, HttpRequest
import csv
from collections import OrderedDict

from django_datatables_view.base_datatable_view import BaseDatatableView
from haystack.query import SearchQuerySet

import json, datetime, urllib.request, urllib.parse, urllib.error

from django.shortcuts import render
from formtools.wizard.views import SessionWizardView
from django.conf import settings
from courselib.storage import UploadedFileStorage, TemporaryFileStorage
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.core.mail.message import EmailMultiAlternatives
import os

# ACCESS #
def _can_view_ras():
    """
    Allows access to funding admins, and supervisors of (any) RA.

    Request object gets .units and .is_supervisor set along the way.
    """
    def auth_test(request, **kwargs):
        supervisor = RAAppointment.objects.filter(hiring_faculty__userid=request.user.username).exists()
        request.is_supervisor = supervisor
        return has_role('FUND', request, **kwargs) or supervisor

    actual_decorator = user_passes_test(auth_test)
    return actual_decorator


def can_create():
    """
    Allows access to funding admins, and supervisors of (any) RA.

    Request object gets .units and .is_supervisor set along the way.
    """
    def auth_test(request, **kwargs):
        return has_role('FUND', request, **kwargs)

    actual_decorator = user_passes_test(auth_test)
    return actual_decorator

def _can_view_ra_requests():
    """
    Allows access to faculty members, and supervisors and authors of (any) RA.
    """
    def auth_test(request, **kwargs):
        supervisor = RARequest.objects.filter(supervisor__userid=request.user.username, draft=False, deleted=False).exists() or RAAppointment.objects.filter(hiring_faculty__userid=request.user.username).exists()
        author = RARequest.objects.filter(author__userid=request.user.username, draft=False, deleted=False).exists()
        request.is_supervisor = supervisor
        request.is_author = author
        return has_role('FDRE', request, **kwargs) or has_role('FUND', request, **kwargs) or author or supervisor
    
    actual_decorator = user_passes_test(auth_test)
    return actual_decorator

# NEW RA #

FORMS = [("intro", RARequestIntroForm),
         ("dates", RARequestDatesForm),
         ("graduate_research_assistant", RARequestGraduateResearchAssistantForm),
         ("non_continuing", RARequestNonContinuingForm),
         ("research_assistant", RARequestResearchAssistantForm),
         ("funding_sources", RARequestFundingSourceForm),
         ("supporting", RARequestSupportingForm)]

TEMPLATES = {"intro": "ra/new_request/intro.html",
             "dates": "ra/new_request/dates.html",
             "graduate_research_assistant": "ra/new_request/graduate_research_assistant.html",
             "non_continuing": "ra/new_request/non_continuing.html",
             "research_assistant": "ra/new_request/research_assistant.html",
             "funding_sources": "ra/new_request/funding_sources.html",
             "supporting": "ra/new_request/supporting.html"
             }

def _req_defaults(units, emplid=None):
    unit_choices = [(u.id, u.name) for u in units]
    return unit_choices

def check_gras(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step('intro') or {'hiring_category': 'none'}
    return cleaned_data['hiring_category']=='GRAS'

def check_ra(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step('intro') or {'hiring_category': 'none'}
    return cleaned_data['hiring_category']=='RA'
    
def check_nc(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step('intro') or {'hiring_category': 'none'}
    return cleaned_data['hiring_category']=='NC'

# grad funding requestors should not be able to reappoint any appointees that they are not authors or supervisors for
def _reappointment_req(request, ra_slug):
    req = None
    if has_role('FUND', request):
        req = get_object_or_404(RARequest, slug=ra_slug, deleted=False, draft=False, unit__in=request.units)
    elif has_role('FDRE', request):
        req = get_object_or_404(RARequest, Q(author__userid=request.user.username) | Q(supervisor__userid=request.user.username), slug=ra_slug, draft=False, deleted=False)
    return req

# grad funding requestors should not be able to edit any request that are not drafts they are authors for
# admin can only edit drafts that they are authors for
def _edit_req(request, ra_slug):
    req = None
    if has_role('FUND', request):
        req = get_object_or_404(RARequest, Q(draft=False) | Q(draft=True, author__userid=request.user.username), slug=ra_slug, deleted=False, unit__in=request.units)
    elif has_role('FDRE', request):
        req = get_object_or_404(RARequest, author__userid=request.user.username, slug=ra_slug, deleted=False, draft=True)
    return req

def _email_request_notification(req, url):
    """
    Email notification to responsible role accounts.
    """
    subject = "New Research Personnel Appointment Request Form Submission" 
    from_email = req.author.email()
    email = None
    if req.hiring_category == "GRAS":
        if req.unit.label == "CMPT":
            email = CS_CONTACT
        elif req.unit.label == "MSE":
            email = MSE_CONTACT
        elif req.unit.label == "ENSC":
            email = None
        elif req.unit.label == "SEE":
            email = SEE_CONTACT
        else:
            email = FAS_CONTACT
    elif req.hiring_category == "RA" or req.hiring_category == "NC":
        email = FAS_CONTACT

    if email:
        content_text = req.author.name() + " has submitted a new Research Personnel Appointment Request Form. You can view it here: " + url
        mail = EmailMultiAlternatives(subject=subject, body=content_text, from_email=from_email, to=[email])
        mail.send()

@method_decorator([requires_role(["FUND", "FDRE"]), never_cache], name='dispatch')
class RANewRequestWizard(SessionWizardView):

    file_storage = TemporaryFileStorage

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]
    
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        reappoint = 'ra_slug' in self.kwargs
        context.update({'fas_contact': FAS_CONTACT})
        if self.steps.current == 'intro':
            context.update({'ura_contact': URA_CONTACT, 
                            'pd_contact': PD_CONTACT, 
                            'cs_contact': CS_CONTACT, 
                            'mse_contact': MSE_CONTACT, 
                            'see_contact': SEE_CONTACT, 
                            'ensc_contact': ENSC_CONTACT, 
                            'deans_contact': DEANS_CONTACT})
        if self.steps.current == 'funding_sources':
            cleaned_data = self.get_cleaned_data_for_step('dates') or {}
            context.update({'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date']})
            cleaned_data_intro = self.get_cleaned_data_for_step('intro')
            hiring_category = cleaned_data_intro['hiring_category']
            pay_data = {}
            if hiring_category == "GRAS":
                pay_data = self.get_cleaned_data_for_step('graduate_research_assistant')
            elif hiring_category == "RA":
                pay_data = self.get_cleaned_data_for_step('research_assistant')
            elif hiring_category == "NC":
                pay_data = self.get_cleaned_data_for_step('non_continuing')
            context.update({'total_pay': pay_data['total_pay']})
        if reappoint:
            ra_slug = self.kwargs['ra_slug']
            req = _reappointment_req(self.request, ra_slug)    
            context.update({'reappoint': True, 'slug': ra_slug, 'admin': has_role('FUND', self.request)})
        else: 
            context.update({'admin': has_role('FUND', self.request)})
        context.update({'draft_option': True})
        return context

    def get_form_kwargs(self, step):
        step = step or self.steps.current
        kwargs = super(RANewRequestWizard, self).get_form_kwargs(step)

        if step=='research_assistant':
            intro = self.get_cleaned_data_for_step('intro') or {}
            if intro['coop']=="True": 
                kwargs['coop'] = True
            if intro['usra']:
                kwargs['usra'] = True
        if step=='non_continuing':
            intro = self.get_cleaned_data_for_step('intro') or {}
            if intro['coop']=="True": 
                kwargs['coop'] = True
        return kwargs

    def get_form_initial(self, step):
        init = {}
        reappoint = 'ra_slug' in self.kwargs
        if reappoint:
            ra_slug = self.kwargs['ra_slug']
            req = _reappointment_req(self.request, ra_slug)        
        if step == 'intro' and reappoint:
            if req.nonstudent:
                init = {'supervisor': req.supervisor.emplid}
            if req.person:
                init = {'supervisor': req.supervisor.emplid, 'person': req.person.emplid}
        if step == 'non_continuing':
            cleaned_data = self.get_cleaned_data_for_step('dates') or {}
            init = {'pay_periods': cleaned_data['pay_periods'], 'backdated': cleaned_data['backdated'], 'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date']}
        if step == 'research_assistant':
            cleaned_data = self.get_cleaned_data_for_step('dates') or {}
            init = {'pay_periods': cleaned_data['pay_periods'], 'backdated': cleaned_data['backdated'], 'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date']}
        if step == 'graduate_research_assistant':
            cleaned_data = self.get_cleaned_data_for_step('dates') or {}
            init = {'pay_periods': cleaned_data['pay_periods'], 'backdated': cleaned_data['backdated'], 'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date']}
        if step == 'funding_sources':
            cleaned_data = self.get_cleaned_data_for_step('dates') or {}
            cleaned_data_intro = self.get_cleaned_data_for_step('intro')
            hiring_category = cleaned_data_intro['hiring_category']
            pay_data = {}
            if hiring_category == "GRAS":
                pay_data = self.get_cleaned_data_for_step('graduate_research_assistant')
            elif hiring_category == "RA":
                pay_data = self.get_cleaned_data_for_step('research_assistant')
            elif hiring_category == "NC":
                pay_data = self.get_cleaned_data_for_step('non_continuing')
            # roll over start and end dates for validation, and initialize start dates of funding sources to overall start and end dates if not edit
            if reappoint:
                init = {'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date'],
                'fs1_start_date': req.fs1_start_date, 'fs2_start_date': req.fs2_start_date, 'fs3_start_date': req.fs3_start_date,
                'fs1_end_date': req.fs1_end_date, 'fs2_end_date': req.fs2_end_date, 'fs3_end_date': req.fs3_end_date, 'total_pay': pay_data['total_pay']}
            else:
                init = {'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date'],
                'fs1_start_date': cleaned_data['start_date'], 'fs2_start_date': cleaned_data['start_date'], 'fs3_start_date': cleaned_data['start_date'],
                'fs1_end_date': cleaned_data['end_date'], 'fs2_end_date': cleaned_data['end_date'], 'fs3_end_date': cleaned_data['end_date'], 'total_pay': pay_data['total_pay']}
        return self.initial_dict.get(step, init)

    def get_form_instance(self, step):
        reappoint = 'ra_slug' in self.kwargs
        if reappoint:
            ra_slug = self.kwargs['ra_slug']
            req = _reappointment_req(self.request, ra_slug)
            # start and end dates on funding source form should be populated by whatever is entered on the dates form, regardless of edit/reappoint
            if step == "funding_sources":
                req.start_date = None
                req.end_date = None
            # reappointments should not include documents from original appointment
            if step == "supporting":
                req.file_attachment_1 = ''
                req.file_mediatype_1 = ''
                req.file_attachment_2 = ''
                req.file_mediatype_2 = ''
            return req
        return self.instance_dict.get(step, None)

    def get_form(self, step=None, data=None, files=None):
        form = super(RANewRequestWizard, self).get_form(step, data, files)

        step = step or self.steps.current
        if step == 'intro': 
            unit_choices = _req_defaults(self.request.units)
            form.fields['unit'].choices = unit_choices
        # the following allows the user to complete all steps before submission, but then still be able to go back and change dates (which changes pay periods and backdated status)
        # we need pay periods and backdated status to be dynamic in this way because they are being used for JS calculations
        if data:
            data = form.data.copy()
            if step == 'research_assistant':
                    cleaned_data = self.get_cleaned_data_for_step('dates') or {}
                    data['research_assistant-pay_periods'] = float(cleaned_data['pay_periods'])
                    data['research_assistant-backdated'] = cleaned_data['backdated']
                    form = super(RANewRequestWizard, self).get_form(step, data)
            if step == 'non_continuing':
                    cleaned_data = self.get_cleaned_data_for_step('dates') or {}
                    data['non_continuing-pay_periods'] = float(cleaned_data['pay_periods'])
                    data['non_continuing-backdated'] = cleaned_data['backdated']
                    form = super(RANewRequestWizard, self).get_form(step, data)
            if step == 'graduate_research_assistant':
                    cleaned_data = self.get_cleaned_data_for_step('dates') or {}
                    data['graduate_research_assistant-pay_periods'] = float(cleaned_data['pay_periods'])
                    data['graduate_research_assistant-backdated'] = cleaned_data['backdated']
                    form = super(RANewRequestWizard, self).get_form(step, data)
        return form

    def process_step(self, form):
        if self.steps.current == 'intro' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm)])
        if self.steps.current == 'dates' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm), ("dates", RARequestDatesForm)])
        if self.steps.current == 'graduate_research_assistant' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm), ("dates", RARequestDatesForm), ("graduate_research_assistant", RARequestGraduateResearchAssistantForm)])
        if self.steps.current == 'non_continuing' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm), ("dates", RARequestDatesForm), ("non_continuing", RARequestNonContinuingForm)])
        if self.steps.current == 'research_assistant' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm), ("dates", RARequestDatesForm), ("research_assistant", RARequestResearchAssistantForm)])
        if self.steps.current == 'funding_sources' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm), ("dates", RARequestDatesForm), ("graduate_research_assistant", RARequestGraduateResearchAssistantForm), 
                            ("non_continuing", RARequestNonContinuingForm), ("research_assistant", RARequestResearchAssistantForm), ("funding_sources", RARequestFundingSourceForm)])
        return self.get_form_step_data(form)

    def done(self, form_list, **kwargs):
        req = RARequest()
        for form in form_list:
            for field, value in form.cleaned_data.items():
                setattr(req, field, value)

        req.author = get_object_or_404(Person, userid=self.request.user.username)
        req.mitacs = ""

        if req.hiring_category=="GRAS":
            req.ra_payment_method = None
            req.nc_payment_method = None
        if req.hiring_category=="RA":
            req.gras_payment_method = None
            req.nc_payment_method = None
        if req.hiring_category=="NC":
            req.gras_payment_method = None
            req.ra_payment_method = None

        if 'supporting-file_attachment_1' in self.request.FILES:
            upfile = self.request.FILES['supporting-file_attachment_1']
            req.file_mediatype_1 = upfile.content_type

        if 'supporting-file_attachment_2' in self.request.FILES:
            upfile = self.request.FILES['supporting-file_attachment_2']
            req.file_mediatype_2 = upfile.content_type

        # check to make sure ClearableFileField did not set file to False when clearing
        if req.file_attachment_1 == False:
            req.file_attachment_1 = ''
            req.file_mediatype_1 = ''
        if req.file_attachment_2 == False:
            req.file_attachment_2 = ''
            req.file_mediatype_2 = ''

        # ensure swpp is false if not applicable
        if req.coop == "False" or req.coop == False or req.hiring_category=="GRAS":
            req.swpp = False
        
        # ensure swpp and ra_benefits are false if not applicable
        if req.usra == "True" or req.usra == True:
            req.swpp = False
            req.ra_benefits = "N"

        # if user creates request as draft
        if self.request.POST.get("save_draft"):
            req.draft = True
            if not req.total_pay:
                req.total_pay = 0
        else:
            req.draft = False
            req.build_letter_text()

        req.save()

        if req.draft:
            description = "Created RA Request Draft %s." % req
            messages.success(self.request, 'Created RA Request Draft')
        else: 
            description = "Created RA Request %s." % req
            messages.success(self.request, 'Created RA Request for ' + req.get_name())
            url = self.request.build_absolute_uri(reverse('ra:view_request', kwargs={'ra_slug': req.slug}))
            _email_request_notification(req, url)

        l = LogEntry(userid=self.request.user.username,
                        description=description,
                        related_object=req)
        l.save()

        if req.draft: 
            return HttpResponseRedirect(reverse('ra:browse_appointments'))
        else:
            return HttpResponseRedirect(reverse('ra:view_request', kwargs={'ra_slug': req.slug}))

@method_decorator([requires_role(["FUND", "FDRE"]), never_cache], name='dispatch')
class RAEditRequestWizard(SessionWizardView):
    file_storage = TemporaryFileStorage

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]
    
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context.update({'fas_contact': FAS_CONTACT})
        if self.steps.current == 'intro':
            context.update({'ura_contact': URA_CONTACT, 
                            'pd_contact': PD_CONTACT, 
                            'cs_contact': CS_CONTACT, 
                            'mse_contact': MSE_CONTACT, 
                            'see_contact': SEE_CONTACT, 
                            'ensc_contact': ENSC_CONTACT, 
                            'deans_contact': DEANS_CONTACT})
        if self.steps.current == 'funding_sources':
            cleaned_data = self.get_cleaned_data_for_step('dates') or {}
            context.update({'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date']})
            cleaned_data_intro = self.get_cleaned_data_for_step('intro')
            hiring_category = cleaned_data_intro['hiring_category']
            pay_data = {}
            if hiring_category == "GRAS":
                pay_data = self.get_cleaned_data_for_step('graduate_research_assistant')
            elif hiring_category == "RA":
                pay_data = self.get_cleaned_data_for_step('research_assistant')
            elif hiring_category == "NC":
                pay_data = self.get_cleaned_data_for_step('non_continuing')
            context.update({'total_pay': pay_data['total_pay']})
        ra_slug = self.kwargs['ra_slug']
        req = _edit_req(self.request, ra_slug)
        context.update({'edit': True, 'draft': req.draft, 'slug': ra_slug, 'name': req.get_name(), 'admin': has_role('FUND', self.request), 'status': req.status()})
        return context

    def get_form_kwargs(self, step):
        step = step or self.steps.current
        ra_slug = self.kwargs['ra_slug']
        req = _edit_req(self.request, ra_slug)

        kwargs = super(RAEditRequestWizard, self).get_form_kwargs(step)
        if step == 'dates' and not req.draft:
            kwargs['edit'] = True
        if step=='research_assistant':
            intro = self.get_cleaned_data_for_step('intro') or {}
            if intro['coop']=="True": 
                kwargs['coop'] = True
            if intro['usra']:
                kwargs['usra'] = True
        if step=='graduate_research_assistant':
            if req.complete:
                kwargs['complete'] = True
        if step=='non_continuing':
            intro = self.get_cleaned_data_for_step('intro') or {}
            if intro['coop']=="True": 
                kwargs['coop'] = True
        return kwargs

    def get_form_initial(self, step):
        init = {}
        ra_slug = self.kwargs['ra_slug']
        req = _edit_req(self.request, ra_slug)
        if step == 'intro':
            if req.nonstudent:
                init = {'supervisor': req.supervisor.emplid}
            if req.person:
                init = {'supervisor': req.supervisor.emplid, 'person': req.person.emplid}
        if step == 'non_continuing':
            cleaned_data = self.get_cleaned_data_for_step('dates') or {}
            init = {'pay_periods': cleaned_data['pay_periods'], 'backdated': cleaned_data['backdated'], 'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date']}
        if step == 'research_assistant':
            cleaned_data = self.get_cleaned_data_for_step('dates') or {}
            init = {'pay_periods': cleaned_data['pay_periods'], 'backdated': cleaned_data['backdated'], 'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date']}
        if step == 'graduate_research_assistant':
            cleaned_data = self.get_cleaned_data_for_step('dates') or {}
            init = {'pay_periods': cleaned_data['pay_periods'], 'backdated': cleaned_data['backdated'], 'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date']}
        if step == 'funding_sources':
            cleaned_data = self.get_cleaned_data_for_step('dates') or {}
            cleaned_data_intro = self.get_cleaned_data_for_step('intro')
            hiring_category = cleaned_data_intro['hiring_category']
            pay_data = {}
            if hiring_category == "GRAS":
                pay_data = self.get_cleaned_data_for_step('graduate_research_assistant')
            elif hiring_category == "RA":
                pay_data = self.get_cleaned_data_for_step('research_assistant')
            elif hiring_category == "NC":
                pay_data = self.get_cleaned_data_for_step('non_continuing')
            init = {'start_date': cleaned_data['start_date'], 'end_date': cleaned_data['end_date'],
                'fs1_start_date': req.fs1_start_date, 'fs2_start_date': req.fs2_start_date, 'fs3_start_date': req.fs3_start_date,
                'fs1_end_date': req.fs1_end_date, 'fs2_end_date': req.fs2_end_date, 'fs3_end_date': req.fs3_end_date, 'total_pay': pay_data['total_pay']}
        return self.initial_dict.get(step, init)

    def get_form_instance(self, step):
        ra_slug = self.kwargs['ra_slug']
        req = _edit_req(self.request, ra_slug)
        return req

    def get_form(self, step=None, data=None, files=None):
        form = super(RAEditRequestWizard, self).get_form(step, data, files)
        step = step or self.steps.current
        if step == 'intro': 
            unit_choices = _req_defaults(self.request.units)
            form.fields['unit'].choices = unit_choices
        if data:
            data = form.data.copy()
            if step == 'research_assistant':
                    cleaned_data = self.get_cleaned_data_for_step('dates') or {}
                    data['research_assistant-pay_periods'] = float(cleaned_data['pay_periods'])
                    data['research_assistant-backdated'] = cleaned_data['backdated']
                    form = super(RAEditRequestWizard, self).get_form(step, data)
            if step == 'non_continuing':
                    cleaned_data = self.get_cleaned_data_for_step('dates') or {}
                    data['non_continuing-pay_periods'] = float(cleaned_data['pay_periods'])
                    data['non_continuing-backdated'] = cleaned_data['backdated']
                    form = super(RAEditRequestWizard, self).get_form(step, data)
            if step == 'graduate_research_assistant':
                    cleaned_data = self.get_cleaned_data_for_step('dates') or {}
                    data['graduate_research_assistant-pay_periods'] = float(cleaned_data['pay_periods'])
                    data['graduate_research_assistant-backdated'] = cleaned_data['backdated']
                    form = super(RAEditRequestWizard, self).get_form(step, data)
        return form

    def process_step(self, form):
        if self.steps.current == 'intro' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm)])
        if self.steps.current == 'dates' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm), ("dates", RARequestDatesForm)])
        if self.steps.current == 'graduate_research_assistant' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm), ("dates", RARequestDatesForm), ("graduate_research_assistant", RARequestGraduateResearchAssistantForm)])
        if self.steps.current == 'non_continuing' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm), ("dates", RARequestDatesForm), ("non_continuing", RARequestNonContinuingForm)])
        if self.steps.current == 'research_assistant' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm), ("dates", RARequestDatesForm), ("research_assistant", RARequestResearchAssistantForm)])
        if self.steps.current == 'funding_sources' and self.request.POST.get("save_draft"):
            self.form_list = OrderedDict([("intro", RARequestIntroForm), ("dates", RARequestDatesForm), ("graduate_research_assistant", RARequestGraduateResearchAssistantForm), 
                            ("non_continuing", RARequestNonContinuingForm), ("research_assistant", RARequestResearchAssistantForm), ("funding_sources", RARequestFundingSourceForm)])
        return self.get_form_step_data(form)

    def done(self, form_list, **kwargs):
        ra_slug = self.kwargs['ra_slug']
        req = get_object_or_404(RARequest, slug=ra_slug, deleted=False, unit__in=self.request.units) 
        for form in form_list:
            for field, value in form.cleaned_data.items():
                setattr(req, field, value)

        submission = False

        # if user is editing a draft
        if self.request.POST.get("save_draft"):
            if not req.total_pay:
                req.total_pay = 0
        else:
            # if it was a draft when they submitted
            if req.draft:
                submission = True
            
        if submission:
            req.draft = False
            req.build_letter_text()
            req.created_at = datetime.datetime.now()
            # email
            url = self.request.build_absolute_uri(reverse('ra:view_request', kwargs={'ra_slug': req.slug}))
            _email_request_notification(req, url)

        if 'supporting-file_attachment_1' in self.request.FILES:
            upfile = self.request.FILES['supporting-file_attachment_1']
            req.file_mediatype_1 = upfile.content_type

        if 'supporting-file_attachment_2' in self.request.FILES:
            upfile = self.request.FILES['supporting-file_attachment_2']
            req.file_mediatype_2 = upfile.content_type

        # check to make sure ClearableFileField did not set file to False when clearing
        if req.file_attachment_1 == False:
            req.file_attachment_1 = ''
            req.file_mediatype_1 = ''
        if req.file_attachment_2 == False:
            req.file_attachment_2 = ''
            req.file_mediatype_2 = ''

        if req.hiring_category=="GRAS":
            req.ra_payment_method = None
            req.nc_payment_method = None
            req.science_alive = False
        if req.hiring_category=="RA":
            req.gras_payment_method = None
            req.nc_payment_method = None
        if req.hiring_category=="NC":
            req.gras_payment_method = None
            req.ra_payment_method = None

        # ensure swpp is false if not applicable
        if req.coop == "False" or req.coop == False or req.hiring_category=="GRAS":
            req.swpp = False
        
        # ensure swpp and ra_benefits are false if not applicable
        if req.usra == "True" or req.usra == True:
            req.swpp = False
            req.ra_benefits = "N"

        # draft was submitted 
        if submission:
            description = "Submitted RA Request Draft %s." % req
            messages.success(self.request, 'Submitted RA Request Draft')
        # editing a draft
        elif req.draft:
            description = "Edited RA Request Draft %s." % req
            messages.success(self.request, 'Edited RA Request Draft')
        # regular edit
        else: 
            description = "Edited RA Request %s." % req
            messages.success(self.request, 'Edited RA ' + req.status() + ' for ' + req.get_name())
            req.last_updater = get_object_or_404(Person, userid=self.request.user.username)
        
        req.save()

        l = LogEntry(userid=self.request.user.username,
                        description=description,
                        related_object=req)
        l.save()

        if req.draft: 
            return HttpResponseRedirect(reverse('ra:browse_appointments'))
        else:
            return HttpResponseRedirect(reverse('ra:view_request', kwargs={'ra_slug': req.slug}))

@requires_role("FUND")
def dashboard(request: HttpRequest) -> HttpResponse:
    """
    View to see all RA requests
    """
    non_continuing = RARequest.objects.filter(deleted=False, unit__in=request.units, hiring_category="NC", complete=False, draft=False)
    research_assistant = RARequest.objects.filter(deleted=False, unit__in=request.units, hiring_category="RA", complete=False, draft=False)
    graduate_research_assistant = RARequest.objects.filter(deleted=False, unit__in=request.units, hiring_category="GRAS", complete=False, draft=False)
    return render(request, 'ra/dashboards/dashboard.html', {'non_continuing': non_continuing, 'research_assistant': research_assistant, 'graduate_research_assistant': graduate_research_assistant })

@requires_role("FUND")
def active_appointments(request: HttpRequest) -> HttpResponse:
    """ 
    View to see all RA appointments that are currently active
    """
    today = datetime.date.today()
    slack = 14 
    non_continuing = RARequest.objects.filter(deleted=False, unit__in=request.units, hiring_category="NC", complete=True, draft=False, start_date__lte=today + datetime.timedelta(days=slack), end_date__gte=today - datetime.timedelta(days=slack))
    research_assistant = RARequest.objects.filter(deleted=False, unit__in=request.units, hiring_category="RA", complete=True, draft=False, start_date__lte=today + datetime.timedelta(days=slack), end_date__gte=today - datetime.timedelta(days=slack))
    graduate_research_assistant = RARequest.objects.filter(deleted=False, unit__in=request.units, hiring_category="GRAS", complete=True, draft=False, start_date__lte=today + datetime.timedelta(days=slack), end_date__gte=today - datetime.timedelta(days=slack))
    return render(request, 'ra/dashboards/active_appointments.html', {'non_continuing': non_continuing, 'research_assistant': research_assistant, 'graduate_research_assistant': graduate_research_assistant })

@_can_view_ra_requests()
def browse_appointments(request):
    """
    View to browse RA appointments and any requests that the user is supervisor for or has authored
    """
    if 'tabledata' in request.GET:
        return RARequestDataJson.as_view()(request)
    # for supervisors to see any of their current requests
    reqs = RARequest.objects.filter(Q(supervisor__userid=request.user.username) | Q(author__userid=request.user.username), deleted=False, complete=False, draft=False)
    drafts = RARequest.objects.filter(author__userid=request.user.username, deleted=False, complete=False, draft=True)
    processing = RARequest.objects.filter(processor__userid=request.user.username, deleted=False, complete=False, draft=False)
    form = RABrowseForm()
    admin = has_role('FUND', request)
    context = {'form': form, 'reqs': reqs, 'admin': admin, 'drafts': drafts, 'processing': processing}
    return render(request, 'ra/dashboards/browse_appointments.html', context)

@requires_role("FUND")
def appointee_appointments(request: HttpRequest, userid) -> HttpResponse:
    """
    View to see all RA Requests/Appointments where a specific person is an appointee.
    """
    person = get_object_or_404(Person, find_userid_or_emplid(userid))
    reqs = RARequest.objects.filter(person=person, unit__in=request.units, deleted=False, complete=False, draft=False).order_by("-created_at")
    appointments = RARequest.objects.filter(person=person, unit__in=request.units, deleted=False, complete=True, draft=False).order_by("-created_at")
    historic_appointments = RAAppointment.objects.filter(person=person, unit__in=request.units, deleted=False).order_by("-created_at")
    grads = GradStudent.objects.filter(person=person, program__unit__in=request.units)
    context = {'reqs': reqs, 'appointments': appointments, 'historic_appointments': historic_appointments, 'person': person, 'grads': grads}
    return render(request, 'ra/search/appointee_appointments.html', context)

@requires_role("FUND")
def supervisor_appointments(request: HttpRequest, userid) -> HttpResponse:
    """
    View to see all RA Requests/Appointments where a specific person is a supervisor.
    """
    person = get_object_or_404(Person, find_userid_or_emplid(userid))
    reqs = RARequest.objects.filter(supervisor=person, unit__in=request.units, deleted=False, complete=False, draft=False).order_by("-created_at")
    appointments = RARequest.objects.filter(supervisor=person, unit__in=request.units, deleted=False, complete=True, draft=False).order_by("-created_at")
    historic_appointments = RAAppointment.objects.filter(hiring_faculty=person, unit__in=request.units, deleted=False).order_by("-created_at")
    context = {'reqs': reqs, 'appointments': appointments, 'historic_appointments': historic_appointments, 'person': person}
    return render(request, 'ra/search/supervisor_appointments.html', context)

#This is the search function that that returns a list of RA Appointments related to the query.
@requires_role("FUND")
def advanced_search(request):
    """
    View for all search options
    """
    if request.method == 'POST':
        appointee_form = AppointeeSearchForm()
        supervisor_form = SupervisorSearchForm()
        if 'appointee_submit' in request.POST:
            appointee_form = AppointeeSearchForm(request.POST)
            if appointee_form.is_valid():
                person = appointee_form.cleaned_data['appointee']
                if person.userid:
                    userid = person.userid
                else:
                    userid = person.emplid
                return HttpResponseRedirect(reverse('ra:appointee_appointments', kwargs={'userid': userid}))
        elif 'supervisor_submit' in request.POST:
            supervisor_form = SupervisorSearchForm(request.POST)
            if supervisor_form.is_valid():
                person = supervisor_form.cleaned_data['supervisor']
                if person.userid:
                    userid = person.userid
                else:
                    userid = person.emplid
                return HttpResponseRedirect(reverse('ra:supervisor_appointments', kwargs={'userid': userid}))
    else:
        appointee_form = AppointeeSearchForm()
        supervisor_form = SupervisorSearchForm()
    context = {'supervisor_form': supervisor_form, 'appointee_form': appointee_form}
    return render(request, 'ra/search/advanced_search.html', context)

# View RA Request/Appointment
@_can_view_ra_requests()
def view_request(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    View to view a RA request.
    """
    admin = has_role('FUND', request)
    user = get_object_or_404(Person, userid=request.user.username)

    if admin:
        req = get_object_or_404(RARequest, Q(unit__in=request.units), slug=ra_slug, draft=False, deleted=False)
    else:
        req = get_object_or_404(RARequest, Q(author__userid=request.user.username) | Q(supervisor__userid=request.user.username), slug=ra_slug, draft=False, deleted=False)

    person = req.person
    supervisor = req.supervisor
    author = req.author
    last_updater = req.last_updater
    # variables to help filter out unneccesary info to viewer
    research_assistant = (req.hiring_category=="RA")
    non_cont = (req.hiring_category=="NC")
    graduate_research_assistant = (req.hiring_category=="GRAS")
    gras_ls = (graduate_research_assistant and req.gras_payment_method=="LS")
    gras_le = (graduate_research_assistant and req.gras_payment_method=="LE")
    gras_bw = (graduate_research_assistant and req.gras_payment_method=="BW")
    ra_hourly = (research_assistant and req.ra_payment_method=="H")
    ra_bw = (research_assistant and req.ra_payment_method=="BW")
    nc_hourly = (non_cont and req.nc_payment_method=="H")
    nc_bw = (non_cont and req.nc_payment_method=="BW")
    nonstudent = req.student=="N"
    show_research = nonstudent or not req.usra
    show_thesis = not nonstudent and req.research
    show_mitacs = (req.mitacs == True or req.mitacs == False)
    is_processor = (user == req.processor)

    adminform = RARequestAdminForm(instance=req)

    return render(request, 'ra/view_request.html',
        {'req': req, 'person': person, 'supervisor': supervisor, 'nonstudent': nonstudent, 'no_id': req.nonstudent,
         'author': author, 'graduate_research_assistant': graduate_research_assistant, 'research_assistant': research_assistant, 'non_cont': non_cont, 
         'gras_le': gras_le, 'gras_ls': gras_ls, 'gras_bw': gras_bw, 'ra_hourly': ra_hourly, 'ra_bw': ra_bw, 'nc_bw': nc_bw, 'nc_hourly': nc_hourly, 
         'show_thesis': show_thesis, 'show_research': show_research, 'show_mitacs': show_mitacs, 'adminform': adminform, 'admin': admin, 
         'permissions': request.units, 'status': req.status(), 'is_processor': is_processor})

@requires_role("FUND")
def update_processor(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    Update Processor
    """
    user = get_object_or_404(Person, userid=request.user.username)
    req = get_object_or_404(RARequest, slug=ra_slug, deleted=False, draft=False, complete=False, unit__in=request.units)

    if not req.processor:
        description = "Assigned themselves as processor for Request %s." % req
        req.processor = user
    elif req.processor == user:
        description = "Unassigned themselves as processor for Request %s." % req
        req.processor = None
    else:
        description = "Unassigned %s as processor and assigned themselves for Request %s" % (req.processor, req)
        req.processor = user
    
    req.last_updater = user
    req.save()

    l = LogEntry(userid=request.user.username,
            description=description,
            related_object=req)
    l.save()              
    messages.success(request, "Updated Processor for Request %s" % req.get_name())
    
    return HttpResponseRedirect(reverse('ra:view_request', kwargs={'ra_slug': req.slug}))


# Update admin checklist
@requires_role("FUND")
def request_admin_update(request: HttpRequest, ra_slug: str) -> HttpResponse:
    req = get_object_or_404(RARequest, slug=ra_slug, deleted=False, draft=False, unit__in=request.units)
    if request.method == 'POST':
        data = request.POST.copy()
        adminform = RARequestAdminForm(data, instance=req)
        if adminform.is_valid():
            req.complete = req.get_complete()
            req.last_updater = get_object_or_404(Person, userid=request.user.username)
            req = adminform.save()

            if req.complete:
                description = "Updated Progress for Request %s. Complete! Appointment has now been created."
            else:
                description = "Updated Progress for Request %s."
            l = LogEntry(userid=request.user.username,
                         description=description % req,
                         related_object=req)
            l.save()
            messages.success(request, description % req.get_name())
    
    return HttpResponseRedirect(reverse('ra:view_request', kwargs={'ra_slug': req.slug}))

@requires_role(["FUND", "FDRE"])
def delete_request_draft(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    View to delete a RA Request Draft.
    """
    req = get_object_or_404(RARequest, slug=ra_slug, author__userid=request.user.username, deleted=False, complete=False, draft=True)
    if request.method == 'POST':
        req.deleted = True
        req.save()
        messages.success(request, "Deleted RA Request Draft.")
        l = LogEntry(userid=request.user.username,
              description="Deleted RA Request Draft %s." % (str(req),),
              related_object=req)
        l.save()              
    
    return HttpResponseRedirect(reverse('ra:browse_appointments'))

@requires_role("FUND")
def delete_request(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    View to delete a RA request.
    """
    req = get_object_or_404(RARequest, slug=ra_slug, deleted=False, draft=False, unit__in=request.units)
    if request.method == 'POST':
        req.deleted = True
        req.save()
        messages.success(request, "Deleted RA Request." )
        l = LogEntry(userid=request.user.username,
              description="Deleted RA Request %s." % (str(req),),
              related_object=req)
        l.save()              
    
    return HttpResponseRedirect(reverse('ra:dashboard'))

@requires_role("FUND")
def edit_request_notes(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    View to edit notes of an RA request.
    """
    req = get_object_or_404(RARequest, slug=ra_slug, deleted=False, draft=False, unit__in=request.units)
    
    if request.method == 'POST':
        noteform = RARequestNoteForm(request.POST, instance=req)
        
        if noteform.is_valid():
            req.last_updater = get_object_or_404(Person, userid=request.user.username)
            noteform.save()
            messages.success(request, "Edited Note for " + req.get_name())
            l = LogEntry(userid=request.user.username,
                description="Edited Note for RA Request %s" % (str(req),),
                related_object=req)
            l.save()              
            return HttpResponseRedirect(reverse('ra:view_request', kwargs={'ra_slug': req.slug}))
    else: 
        noteform = RARequestNoteForm(instance=req)
    return render(request, 'ra/admin/edit_request_notes.html', {'noteform': noteform, 'req':req, 'status': req.status()})

@requires_role("FUND")
def request_offer_letter(request: HttpRequest, ra_slug: str) -> HttpResponse:
    req = get_object_or_404(RARequest, Q(backdated=False) | Q(hiring_category__in=['GRAS']), slug=ra_slug, unit__in=request.units, deleted=False, draft=False)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="%s-letter.pdf"' % (req.slug)
    letter = FASOfficialLetter(response)
    from_name_lines = [req.supervisor.letter_name(), req.unit.name]
    if req.additional_supervisor and req.additional_department:
        extra_from_name_lines = [req.additional_supervisor, req.additional_department]
    else:
        extra_from_name_lines = None
    contents = LetterContents(
        to_addr_lines=[req.get_name(), req.unit.name], 
        from_name_lines=from_name_lines,
        extra_from_name_lines = extra_from_name_lines,
        closing="Yours truly", 
        signer=req.supervisor,
        cosigner_lines=[req.get_cosigner_line(), req.get_first_name() + " " + req.get_last_name()])
    contents.add_paragraphs(["Dear " + req.get_name()])
    try:
        contents.add_paragraphs(req.letter_paragraphs())
    except ValueError as e:
        messages.error(request, f'Could not render letter. Error was: {e}')
        return HttpResponseRedirect(reverse('ra:request_offer_letter_update', kwargs={'ra_slug': req.slug}))

    letter.add_letter(contents)
    letter.write()
    return response

# for offer letters
@requires_role("FUND")
def request_offer_letter_update(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """ 
    View to update offer letter text
    """
    req = get_object_or_404(RARequest, Q(backdated=False) | Q(hiring_category__in=['GRAS']), slug=ra_slug, unit__in=request.units, deleted=False, draft=False)

    if request.method == 'POST':
        configform = RARequestLetterForm(request.POST, instance=req)
        if configform.is_valid():
            req.last_updater = get_object_or_404(Person, userid=request.user.username)
            configform.save()
            messages.success(request, 'Updated Letter Text for ' + req.get_name())
            l = LogEntry(userid=request.user.username,
                description="Updated Letter Text for RA Request %s" % (str(req),),
                related_object=req)
            l.save()       
            return HttpResponseRedirect(reverse('ra:request_offer_letter_update', kwargs={'ra_slug': req.slug}))
    else:
        configform = RARequestLetterForm(instance=req)
        saform = RARequestScienceAliveForm()

    research_assistant = (req.hiring_category=="RA")
    non_cont = (req.hiring_category=="NC")
    context = {'req': req, 'configform': configform, 'saform': saform, 'research_assistant': research_assistant, 'non_cont': non_cont, 'status': req.status()}
    return render(request, 'ra/admin/request_offer_letter.html', context) 

@requires_role("FUND")
def request_default_offer_letter(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """ 
    Update offer letter text to default 
    """
    req = get_object_or_404(RARequest, Q(backdated=False) | Q(hiring_category__in=['GRAS']), slug=ra_slug, unit__in=request.units, deleted=False, draft=False)
    if request.method == 'POST':
        req.build_letter_text()
        req.last_updater = get_object_or_404(Person, userid=request.user.username)
        req.save()
        messages.success(request, 'Updated Letter Text for ' + req.get_name())
        l = LogEntry(userid=request.user.username,
              description="Updated Letter Text for RA Request (To Default) %s" % (str(req),),
              related_object=req)
        l.save()              

    return HttpResponseRedirect(reverse('ra:request_offer_letter_update', kwargs={'ra_slug': req.slug}))

@requires_role("FUND")
def request_science_alive(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    Swtich appointment to science alive, or not science alive.
    Impacts offer letter generation.
    """
    req = get_object_or_404(RARequest, slug=ra_slug, hiring_category__in=['RA', 'NC'], deleted=False, unit__in=request.units, backdated=False, draft=False)
    if request.method == 'POST':
        
        if req.hiring_category == "RA" or req.hiring_category=="NC":
            req.science_alive = not req.science_alive
        else: 
            req.science_alive = False
        req.last_updater = get_object_or_404(Person, userid=request.user.username)
        req.save()
        messages.success(request, "Switched Science Alive Status for " + req.get_name())
        l = LogEntry(userid=request.user.username,
              description="Switched Science Alive Status for RA Request %s." % (str(req),),
              related_object=req)
        l.save()              
    
    return HttpResponseRedirect(reverse('ra:request_offer_letter_update', kwargs={'ra_slug': req.slug}))

@requires_role("FUND")
def request_science_alive_letter(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    Configure and download science alive offer letters
    """
    req = get_object_or_404(RARequest, slug=ra_slug, hiring_category__in=['RA', 'NC'], deleted=False, unit__in=request.units, backdated=False, draft=False)
    form = RARequestScienceAliveForm(request.POST)
    if form.is_valid():
        config = ({'letter_type': form.cleaned_data['letter_type'], 'final_bullet': form.cleaned_data['final_bullet']})
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = 'inline; filename="%s.pdf"' % (req.slug)
        ra_science_alive(req, config, response)
        return response
    return HttpResponseRedirect(reverse('ra:request_offer_letter_update', kwargs={'ra_slug': req.slug}))

@requires_role("FUND")
def request_paf(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    View to configure and download payroll appointment form (and show visa info prior to download)
    """
    req = get_object_or_404(RARequest, slug=ra_slug, deleted=False, draft=False, unit__in=request.units)
    if request.method == 'POST':
        form = RARequestPAFForm(request.POST)
        if form.is_valid():
            appointment_type = form.cleaned_data['appointment_type']
            config = ({'appointment_type': form.cleaned_data['appointment_type']})
            response = HttpResponse(content_type="application/pdf")
            response['Content-Disposition'] = 'inline; filename="%s.pdf"' % (req.slug)
            ra_paf(req, config, response)
            return response
    else: 
        form = RARequestPAFForm()
        adminpafform = RARequestAdminPAFForm(instance=req)
    
    # get info on student visas, citizenship and programs (combined person_info and visa_info)
    if req.nonstudent:
        info = {}
    else:
        emplid = req.person.emplid
        grads = GradStudent.objects.filter(person__emplid=emplid, program__unit__in=request.units)
        info = {'programs': [], 'visas': []}
        programs = []
        for gs in grads:
            pdata = {
                    'program': gs.program.label,
                    'unit': gs.program.unit.name,
                    'status': gs.get_current_status_display(),
                    }
            programs.append(pdata)
        info['programs'] = programs
        # other SIMS info
        try:
            otherinfo = more_personal_info(emplid, needed=['citizen', 'visa'])
            info.update(otherinfo)
        except SIMSProblem as e:
            info['error'] = str(e)
        visas = []
        personvisas = Visa.objects.visible().filter(person__emplid=emplid)
        for v in personvisas:
            if v.is_current():
                if v.end_date:
                    end_date = v.end_date.isoformat()
                else:
                    end_date = "Unknown"
                data = {
                    'start': v.start_date.isoformat(),
                    'end': end_date,
                    'status': v.status,
                    'validity': v.get_validity
                }
                visas.append(data)
        info['visas'] = visas

    isCanadian = False
    if 'citizen' in info:
        citizenshipUnknown = False
        if info['citizen'] == 'Canada':
            isCanadian = True
        citizenship = info['citizen']
    else:
        citizenshipUnknown = True
        citizenship = None

    return render(request, 'ra/admin/request_paf.html', {'form':form, 'adminpafform': adminpafform, 'req':req, 'info': info, 'isCanadian': isCanadian, 
                'citizenshipUnknown': citizenshipUnknown, 'citizenship': citizenship, 'status': req.status()})

@requires_role("FUND")
def request_admin_paf_update(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    Update PAF configuration
    """
    req = get_object_or_404(RARequest, slug=ra_slug, deleted=False, draft=False, unit__in=request.units)
    if request.method == 'POST':
        data = request.POST.copy()
        if not req.fs2_option:
            data['fs1_biweekly_split'] = 0
            data['fs1_percentage'] = 100    
            data['fs2_object'] = ''
            data['fs2_program'] = ''
            data['fs2_biweekly_split'] = 0
            data['fs2_percentage'] = 0   
        if not req.fs3_option:
            data['fs3_object'] = ''
            data['fs3_program'] = ''
            data['fs3_biweekly_split'] = 0
            data['fs3_percentage'] = 0   

        adminform = RARequestAdminPAFForm(data, instance=req)
        if adminform.is_valid():
            req.last_updater = get_object_or_404(Person, userid=request.user.username)
            req = adminform.save()
            l = LogEntry(userid=request.user.username,
                         description="Updated PAF Config for Request %s." % req,
                         related_object=req)
            l.save()
            messages.success(request, 'Updated PAF Config for RA Request for ' + req.get_name())
    return HttpResponseRedirect(reverse('ra:request_paf', kwargs={'ra_slug': req.slug}))

@requires_role("FUND")
def view_request_attachment_1(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    View to view the first attachment for an RA request.
    """
    req = get_object_or_404(RARequest, slug=ra_slug, draft=False, deleted=False, unit__in=request.units)
    attachment = req.file_attachment_1
    filename = attachment.name.rsplit('/')[-1]
    resp = HttpResponse(attachment.chunks(), content_type=req.file_mediatype_1)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.size
    return resp

@requires_role("FUND")
def view_request_attachment_2(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    View to view the second attachment for an RA request.
    """
    req = get_object_or_404(RARequest, slug=ra_slug, draft=False, deleted=False, unit__in=request.units)
    attachment = req.file_attachment_2
    filename = attachment.name.rsplit('/')[-1]
    resp = HttpResponse(attachment.chunks(), content_type=req.file_mediatype_2)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.size
    return resp

@requires_role("FUND")
def download_request_attachment_1(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    View to download the first attachment for an RA request.
    """
    req = get_object_or_404(RARequest, slug=ra_slug, draft=False, deleted=False, unit__in=request.units)
    attachment = req.file_attachment_1
    filename = attachment.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.chunks(), content_type=req.file_mediatype_1)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.size
    return resp

@requires_role("FUND")
def download_request_attachment_2(request: HttpRequest, ra_slug: str) -> HttpResponse:
    """
    View to download the second attachment for an RA request.
    """
    req = get_object_or_404(RARequest, slug=ra_slug, draft=False, deleted=False, unit__in=request.units)
    attachment = req.file_attachment_2
    filename = attachment.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.chunks(), content_type=req.file_mediatype_2)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.size
    return resp

@requires_role("FUND")
@transaction.atomic
def new_admin_attachment(request, ra_slug):
    """
    View to add new admin attachments
    """
    req = get_object_or_404(RARequest, slug=ra_slug, draft=False, deleted=False, unit__in=request.units)
    editor = get_object_or_404(Person, userid=request.user.username)

    form = RARequestAdminAttachmentForm()
    context = {"req": req, "attachment_form": form, "status": req.status()}

    if request.method == "POST":
        form = RARequestAdminAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.req = req
            attachment.created_by = editor
            upfile = request.FILES['contents']
            filetype = upfile.content_type
            if upfile.charset:
                filetype += "; charset=" + upfile.charset
            attachment.mediatype = filetype
            attachment.save()
            req.last_updater = get_object_or_404(Person, userid=request.user.username)
            req.save()
            messages.add_message(request, messages.SUCCESS, 'Admin attachment added.')
            l = LogEntry(userid=request.user.username, description="Added admin attachment %s" % attachment, related_object=attachment)
            l.save()
            return HttpResponseRedirect(reverse('ra:view_request', kwargs={'ra_slug': req.slug}))
        else:
            context.update({"attachment_form": form})
    return render(request, 'ra/admin/new_request_attachment.html', context)

@requires_role("FUND")
def view_admin_attachment(request, ra_slug, attach_slug):
    """
    View to view admin attachments
    """
    req = get_object_or_404(RARequest, slug=ra_slug, draft=False, deleted=False, unit__in=request.units)
    attachment = get_object_or_404(req.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp

@requires_role("FUND")
def download_admin_attachment(request, ra_slug, attach_slug):
    """
    View to download admin attachments
    """
    req = get_object_or_404(RARequest, slug=ra_slug, draft=False, deleted=False, unit__in=request.units)
    attachment = get_object_or_404(req.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp

@requires_role("FUND")
def delete_admin_attachment(request, ra_slug, attach_slug):
    """
    Delete an admin attachment
    """
    req = get_object_or_404(RARequest, slug=ra_slug, draft=False, deleted=False, unit__in=request.units)
    attachment = get_object_or_404(req.attachments.all(), slug=attach_slug)
    attachment.hide()
    req.last_updater = get_object_or_404(Person, userid=request.user.username)
    req.save()
    messages.add_message(request, messages.SUCCESS, 'Admin attachment deleted.')
    l = LogEntry(userid=request.user.username, description="Hid admin attachment %s" % attachment, related_object=attachment)
    l.save()
    return HttpResponseRedirect(reverse('ra:view_request', kwargs={'ra_slug': req.slug}))

@_can_view_ra_requests()
def download(request, current=False):
    """
    Download CSVs of appointments and requests
    """
    admin = has_role('FUND', request)

    if admin:
        ras = RARequest.objects.filter(Q(unit__in=request.units), deleted=False, draft=False).order_by('complete')
    else:
        ras = RARequest.objects.filter(Q(author__userid=request.user.username) | Q(supervisor__userid=request.user.username), deleted=False, draft=False, complete=True)

    if current:
        today = datetime.date.today()
        slack = 14  # number of days to fudge the start/end
        ras = ras.filter(start_date__lte=today + datetime.timedelta(days=slack),
                         end_date__gte=today - datetime.timedelta(days=slack), complete=True)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="ras-%s-%s.csv"' % (datetime.datetime.now().strftime('%Y%m%d'),
                                                                            'current' if current else 'all')


    writer = csv.writer(response)
    if admin:
        writer.writerow(['Status', 'Appointee Name', 'Appointee Email', 'ID', 'Unit', 'Position Title', 'Fund', 'Project', 'Supervisor', 'Supervisor Email', 'Start Date', 'End Date', 'Hiring Category', 'Total Pay', 'SWPP', 'Appointee Co-op Status', 'USRA', 'Mitacs', 'Processed By', 'Student Status', 'Object Code', 'True Scholarship Questionnaire'])
        for ra in ras:
            if ra.complete:
                status = "Complete"
            else:
                status = "In Progress"
            if ra.usra:
                usra = " (USRA)"
            else:
                usra = ""
            writer.writerow([status, ra.get_sort_name(), ra.get_email_address(), ra.get_id(), ra.unit.label, ra.position, ra.get_funds(), ra.get_projects(), ra.supervisor.sortname(), ra.supervisor.email(), ra.start_date, ra.end_date, ra.hiring_category + usra, ra.total_pay, ra.swpp, ra.coop, ra.usra, ra.mitacs, ra.get_processor(), ra.get_student_status(), ra.object_code,  ra.get_scholarship_confirmation_complete()])
    else:
        writer.writerow(['Appointee Name', 'ID', 'Unit', 'Fund', 'Project', 'Supervisor', 'Start Date', 'End Date', 'Hiring Category', 'Total Pay'])
        for ra in ras:
            writer.writerow([ra.get_sort_name(), ra.get_id(), ra.unit.label, ra.get_funds(), ra.get_projects(), ra.supervisor.sortname(), ra.start_date, ra.end_date, ra.hiring_category, ra.total_pay])
    return response

# altered RADataJson, to make a very similar browse page, but for RARequests
class RARequestDataJson(BaseDatatableView):
    model = RARequest
    columns = ['person', 'supervisor', 'unit', 'fund', 'project', 'start_date', 'end_date', 'total_pay']
    order_columns = [
        ['person__last_name', 'person__first_name'],
        ['supervisor__last_name', 'supervisor__first_name'],
        'unit__label',
        'fs1_fund',
        'fs1_project',
        'start_date',
        'end_date',
        'total_pay',
    ]
    max_display_length = 500

    def get_initial_queryset(self):
        qs = super(RARequestDataJson, self).get_initial_queryset()
        # do some select related because we'll need them for display later
        qs = qs.select_related('supervisor', 'unit')
        return qs

    def filter_queryset(self, qs):
        GET = self.request.GET

        # limit to those visible to this user
        admin = has_role('FUND', self.request)

        if admin:
            qs = qs.filter(Q(unit__in=self.request.units))
        else:
            qs = qs.filter(Q(supervisor__userid=self.request.user.username) | Q(author__userid=self.request.user.username))

        # only for completed requests (which are then appointments)
        qs = qs.filter(deleted=False, draft=False, complete=True)

        # "current" contracts filter
        if 'current' in GET and GET['current'] == 'yes':
            today = datetime.date.today()
            slack = 14 # number of days to fudge the start/end
            qs = qs.filter(start_date__lte=today + datetime.timedelta(days=slack),
                           end_date__gte=today - datetime.timedelta(days=slack))

        # search box
        srch = GET.get('sSearch', None)
        if srch:
            # get RA set from haystack, and use it to limit our query.
            ra_qs = SearchQuerySet().models(RARequest).filter(text__fuzzy=srch)[:500]
            ra_qs = [r for r in ra_qs if r is not None]
            if ra_qs:
                # ignore very low scores: elasticsearch grabs too much sometimes
                max_score = max(r.score for r in ra_qs)
                ra_pks = (r.pk for r in ra_qs if r.score > max_score/5)
                qs = qs.filter(pk__in=ra_pks)
            else:
                qs = qs.none()
        return qs

    def render_column(self, ra, column):
        if column == 'total_pay':
            return "${:,}".format(ra.total_pay)
        elif column == 'person':
            url = ra.get_absolute_url()
            name = ra.get_sort_name()
            if ra.has_attachments():
                extra_string = '&nbsp; <i class="fa fa-paperclip" title="Attachment(s)"></i>'
            else:
                extra_string = ''
            return '<a href="%s">%s%s</a>' % (escape(url), escape(name), extra_string)
        elif column == 'unit':
            return ra.unit.label
        elif column == 'fund':
            return ra.get_funds()
        elif column == 'project':
            return ra.get_projects()

        return str(getattr(ra, column))

@_can_view_ras()
def browse(request):
    if 'tabledata' in request.GET:
        return RADataJson.as_view()(request)

    form = RABrowseForm()
    context = {'form': form, 'supervisor_only': not request.units}
    return render(request, 'ra/historic/browse.html', context)


class RADataJson(BaseDatatableView):
    model = RAAppointment
    columns = ['person', 'hiring_faculty', 'unit', 'project', 'account', 'start_date', 'end_date', 'lump_sum_pay']
    order_columns = [
        ['person__last_name', 'person__first_name'],
        ['hiring_faculty__last_name', 'hiring_faculty__first_name'],
        'unit__label',
        'project__project_number',
        'account__account_number',
        'start_date',
        'end_date',
        'lump_sum_pay',
    ]
    max_display_length = 500

    def get_initial_queryset(self):
        qs = super(RADataJson, self).get_initial_queryset()
        # do some select related because we'll need them for display later
        qs = qs.select_related('person', 'hiring_faculty', 'unit')
        return qs

    def filter_queryset(self, qs):
        GET = self.request.GET

        # limit to those visible to this user
        qs = qs.filter(
            Q(unit__in=self.request.units)
            | Q(hiring_faculty__userid=self.request.user.username)
        )
        qs = qs.exclude(deleted=True)

        # "current" contracts filter
        if 'current' in GET and GET['current'] == 'yes':
            today = datetime.date.today()
            slack = 14 # number of days to fudge the start/end
            qs = qs.filter(start_date__lte=today + datetime.timedelta(days=slack),
                           end_date__gte=today - datetime.timedelta(days=slack))

        # search box
        srch = GET.get('sSearch', None)
        if srch:
            # get RA set from haystack, and use it to limit our query.
            ra_qs = SearchQuerySet().models(RAAppointment).filter(text__fuzzy=srch)[:500]
            ra_qs = [r for r in ra_qs if r is not None]
            if ra_qs:
                # ignore very low scores: elasticsearch grabs too much sometimes
                max_score = max(r.score for r in ra_qs)
                ra_pks = (r.pk for r in ra_qs if r.score > max_score/5)
                qs = qs.filter(pk__in=ra_pks)
            else:
                qs = qs.none()

        return qs

    def render_column(self, ra, column):
        if column == 'lump_sum_pay':
            return "${:,}".format(ra.lump_sum_pay)
        elif column == 'person':
            url = ra.get_absolute_url()
            name = ra.person.sortname()
            if ra.has_attachments():
                extra_string = '&nbsp; <i class="fa fa-paperclip" title="Attachment(s)"></i>'
            else:
                extra_string = ''
            return '<a href="%s">%s%s</a>' % (escape(url), escape(name), extra_string)
        elif column == 'unit':
            return ra.unit.label

        return str(getattr(ra, column))

@_can_view_ras()
def download_ras(request, current=True):
    """
    download historic RA appointments
    """
    ras = RAAppointment.objects.filter(Q(unit__in=request.units)
                                       | Q(hiring_faculty__userid=request.user.username))\
        .select_related('person', 'hiring_faculty', 'unit', 'project', 'account').exclude(deleted=True)
    if current:
        today = datetime.date.today()
        slack = 14  # number of days to fudge the start/end
        ras = ras.filter(start_date__lte=today + datetime.timedelta(days=slack),
                         end_date__gte=today - datetime.timedelta(days=slack))
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="ras-%s-%s.csv"' % (datetime.datetime.now().strftime('%Y%m%d'),
                                                                            'current' if current else 'all')
    writer = csv.writer(response)
    writer.writerow(['Name', 'ID', 'Hiring Faculty', 'Unit', 'Project', 'Account', 'Start Date', 'End Date', 'Amount'])
    for ra in ras:
        writer.writerow([ra.person.sortname(), ra.person.emplid, ra.hiring_faculty.sortname(), ra.unit.label, ra.project, ra.account, ra.start_date, ra.end_date, ra.lump_sum_pay])
    return response

#Edit RA Appointment
@requires_role("FUND")
def edit(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug, deleted=False, unit__in=request.units)
    scholarship_choices, hiring_faculty_choices, unit_choices, project_choices, account_choices, program_choices = \
        _appointment_defaults(request.units, emplid=appointment.person.emplid)
    if request.method == 'POST':
        data = request.POST.copy()
        if data['pay_frequency'] == 'L':
            # force legal values into the non-submitted (and don't-care) fields for lump sum pay
            data['biweekly_pay'] = 1
            data['hourly_pay'] = 1
            data['hours'] = 1
            data['pay_periods'] = 1
        
        raform = RAForm(data, instance=appointment)
        if raform.is_valid():
            userid = raform.cleaned_data['person'].userid
            appointment = raform.save(commit=False)
            appointment.set_use_hourly(raform.cleaned_data['use_hourly'])
            appointment.save()
            l = LogEntry(userid=request.user.username,
                         description="Edited RA appointment %s." % appointment,
                         related_object=appointment)
            l.save()
            messages.success(request, 'Updated RA Appointment for ' + appointment.person.first_name + " " + appointment.person.last_name)
            return HttpResponseRedirect(reverse('ra:browse'))
    else:
        #The initial value needs to be the person's emplid in the form. Django defaults to the pk, which is not human readable.
        raform = RAForm(instance=appointment, initial={'person': appointment.person.emplid, 'use_hourly': appointment.use_hourly()})
        #As in the new method, choices are restricted to relevant options.
        raform.fields['person'] = forms.CharField(widget=forms.HiddenInput())
        raform.fields['hiring_faculty'].choices = hiring_faculty_choices
        raform.fields['scholarship'].choices = scholarship_choices
        raform.fields['unit'].choices = unit_choices
        raform.fields['project'].choices = project_choices
        raform.fields['account'].choices = account_choices
        raform.fields['program'].choices = program_choices
    return render(request, 'ra/historic/edit.html', { 'raform': raform, 'appointment': appointment, 'person': appointment.person })

#View RA Appointment
@_can_view_ras()
def view(request, ra_slug):
    appointment = get_object_or_404(RAAppointment,
        Q(unit__in=request.units) | Q(hiring_faculty__userid=request.user.username),
        slug=ra_slug, deleted=False)
    student = appointment.person
    return render(request, 'ra/historic/view.html',
        {'appointment': appointment, 'student': student, 'supervisor_only': not request.units})

#View RA Appointment Form (PDF)
@requires_role("FUND")
def form(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug, deleted=False, unit__in=request.units)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="%s.pdf"' % (appointment.slug)
    ra_form(appointment, response)
    return response

@requires_role("FUND")
def letter(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug, deleted=False, unit__in=request.units)
    if not appointment.offer_letter_text:
        letter_choices = RAAppointment.letter_choices(request.units)
        if len(letter_choices) == 1:  # why make them select from one?
            appointment.build_letter_text(letter_choices[0][0])
        else:
            return HttpResponseRedirect(reverse('ra:select_letter', kwargs=({'ra_slug': ra_slug, 'print_only': 'print'})))
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="%s-letter.pdf"' % (appointment.slug)
    letter = OfficialLetter(response, unit=appointment.unit)
    contents = LetterContents(
        to_addr_lines=[appointment.person.name(), 'c/o '+appointment.unit.name], 
        from_name_lines=[appointment.hiring_faculty.letter_name(), appointment.unit.name],
        closing="Yours Truly", 
        signer=appointment.hiring_faculty,
        cosigner_lines=['I agree to the conditions of employment', appointment.person.first_name + " " + appointment.person.last_name])
    contents.add_paragraphs(["Dear " + appointment.person.get_title() + ' ' + appointment.person.last_name])
    contents.add_paragraphs(appointment.letter_paragraphs())
    letter.add_letter(contents)
    letter.write()
    return response

@requires_role("FUND")
def delete_ra(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug, unit__in=request.units)
    if request.method == 'POST':
        appointment.deleted = True
        appointment.save()
        messages.success(request, "Deleted RA appointment." )
        l = LogEntry(userid=request.user.username,
              description="Deleted RA appointment %s." % (str(appointment),),
              related_object=appointment)
        l.save()              
    
    return HttpResponseRedirect(reverse('ra:browse'))

@requires_role("FUND")
@transaction.atomic
def new_attachment(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug, unit__in=request.units)
    editor = get_object_or_404(Person, userid=request.user.username)

    form = RAAppointmentAttachmentForm()
    context = {"appointment": appointment,
               "attachment_form": form}

    if request.method == "POST":
        form = RAAppointmentAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.appointment = appointment
            attachment.created_by = editor
            upfile = request.FILES['contents']
            filetype = upfile.content_type
            if upfile.charset:
                filetype += "; charset=" + upfile.charset
            attachment.mediatype = filetype
            attachment.save()
            return HttpResponseRedirect(reverse('ra:view', kwargs={'ra_slug': appointment.slug}))
        else:
            context.update({"attachment_form": form})

    return render(request, 'ra/historic/appointment_attachment_form.html', context)


@requires_role("FUND")
def view_attachment(request, ra_slug, attach_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug, unit__in=request.units)
    attachment = get_object_or_404(appointment.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role("FUND")
def download_attachment(request, ra_slug, attach_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug, unit__in=request.units)
    attachment = get_object_or_404(appointment.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role("FUND")
def delete_attachment(request, ra_slug, attach_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug, unit__in=request.units)
    attachment = get_object_or_404(appointment.attachments.all(), slug=attach_slug)
    attachment.hide()
    messages.add_message(request,
                         messages.SUCCESS,
                         'Attachment deleted.'
                         )
    l = LogEntry(userid=request.user.username, description="Hid attachment %s" % attachment, related_object=attachment)
    l.save()
    return HttpResponseRedirect(reverse('ra:view', kwargs={'ra_slug': appointment.slug}))

@requires_role("FUND")
def edit_letter(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug, deleted=False, unit__in=request.units)

    if request.method == 'POST':
        form = RALetterForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated RA Letter Text for ' + appointment.person.first_name + " " + appointment.person.last_name)
            return HttpResponseRedirect(reverse('ra:browse'))
    else:
        if not appointment.offer_letter_text:
            letter_choices = RAAppointment.letter_choices(request.units)
            if len(letter_choices) == 1: # why make them select from one?
                appointment.build_letter_text(letter_choices[0][0])
            else:
                return HttpResponseRedirect(reverse('ra:select_letter', kwargs=({'ra_slug': ra_slug})))
        form = RALetterForm(instance=appointment)
    
    context = {'appointment': appointment, 'form': form}
    return render(request, 'ra/historic/edit_letter.html', context)

# If we don't have an appointment letter yet, pick one.
@requires_role("FUND")
def select_letter(request, ra_slug, print_only=None):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug, deleted=False, unit__in=request.units)
    # Forcing sorting of the letter choices so the Standard template is first.
    letter_choices = sorted(RAAppointment.letter_choices(request.units))
    if request.method == 'POST':
        filled_form = LetterSelectForm(data=request.POST, choices=letter_choices)
        if filled_form.is_valid():
            appointment.build_letter_text(filled_form.cleaned_data['letter_choice'])
        if print_only == 'print':
            return HttpResponseRedirect(reverse('ra:letter', kwargs=({'ra_slug': ra_slug})))
        else:
            return HttpResponseRedirect(reverse('ra:edit_letter', kwargs=({'ra_slug': ra_slug})))

    else:
        new_form = LetterSelectForm(choices=letter_choices)
        context = {'form': new_form, 'ra_slug': ra_slug, 'print_only': print_only}
        return render(request, 'ra/historic/select_letter.html', context)

@requires_role("FUND")
def search_scholarships_by_student(request, student_id):
    #check permissions
    roles = Role.all_roles(request.user.username)
    allowed = set(['FUND'])
    if not (roles & allowed):
        return ForbiddenResponse(request, "Not permitted to search scholarships by student.")
    scholarships = Scholarship.objects.filter(student__person__emplid=student_id)
    response = HttpResponse(content_type="application/json")
    data = [{'value': s.pk, 'display': s.scholarship_type.unit.label + ": " + s.scholarship_type.name + " (" + s.start_semester.name + " to " + s.end_semester.name + ")"}  for s in scholarships]
    json.dump(data, response, indent=1)
    return response

def _appointment_defaults(units, emplid=None):
    hiring_faculty_choices = possible_supervisors(units)
    unit_choices = [(u.id, u.name) for u in units]
    project_choices = [(p.id, str(p)) for p in Project.objects.filter(unit__in=units, hidden=False)]
    account_choices = [(a.id, str(a)) for a in Account.objects.filter(unit__in=units, hidden=False)]
    scholarship_choices = [("", '\u2014')]
    if emplid:
        for s in Scholarship.objects.filter(student__person__emplid=emplid):
            scholarship_choices.append((s.pk, s.scholarship_type.unit.label + ": " + s.scholarship_type.name + " (" + s.start_semester.name + " to " + s.end_semester.name + ")"))
    program_choices = [('', "00000, None")] + [(p.id, str(p)) for p in Program.objects.visible_by_unit(units).order_by('program_number')]
    return (scholarship_choices, hiring_faculty_choices, unit_choices, project_choices, account_choices,
            program_choices)

@requires_role("FUND")
def person_info(request):
    """
    Get more info about this person, for AJAX updates on new RA form
    """
    result = {'programs': []}
    emplid = request.GET.get('emplid', None)
    if not emplid or not emplid.isdigit() or len(emplid) != 9:
        pass
    else:
        programs = []
        
        # GradPrograms
        emplid = request.GET['emplid']
        grads = GradStudent.objects.filter(person__emplid=emplid, program__unit__in=request.units)
        for gs in grads:
            pdata = {
                     'program': gs.program.label,
                     'unit': gs.program.unit.name,
                     'status': gs.get_current_status_display(),
                     }
            programs.append(pdata)

        result['programs'] = programs
        
        # other SIMS info
        try:
            otherinfo = more_personal_info(emplid, needed=['citizen', 'visa'])
            result.update(otherinfo)
        except SIMSProblem as e:
            result['error'] = str(e)

    return HttpResponse(json.dumps(result), content_type='application/json;charset=utf-8')


@requires_role("FUND")
def person_visas(request):
    """
    Get info on this person's current visas, for info in the new RA appointment form.
    """
    result = {'visas': []}
    emplid = request.GET.get('emplid', None)
    if not emplid or not emplid.isdigit() or len(emplid) != 9:
        pass
    else:
        visas = []
        personvisas = Visa.objects.visible().filter(person__emplid=emplid, unit__in=request.units)
        for v in personvisas:
            if v.is_current():
                data = {
                    'start': v.start_date.isoformat(),
                    'status': v.status,
                }
                visas.append(data)
        result['visas'] = visas
    return HttpResponse(json.dumps(result), content_type='application/json;charset=utf-8')

def pay_periods(request):
    """
    Calculate number of pay periods between contract start and end dates.
    i.e. number of work days in period / 10
    
    I swear this was easier that doing it in JS, okay?
    """
    day = datetime.timedelta(days=1)
    week = datetime.timedelta(days=7)
    if 'start' not in request.GET or 'end' not in request.GET:
        result = ''
    else:
        st = request.GET['start']
        en = request.GET['end']
        try:
            st = datetime.datetime.strptime(st, "%Y-%m-%d").date()
            en = datetime.datetime.strptime(en, "%Y-%m-%d").date()
        except ValueError:
            result = ''
        else:
            # move start/end into Mon-Fri work week
            if st.weekday() == 5:
                st += 2*day
            elif st.weekday() == 6:
                st += day
            if en.weekday() == 5:
                en -= day
            elif en.weekday() == 6:
                en -= 2*day

            # number of full weeks (until sameday: last same weekday before end date)
            weeks = ((en-st)/7).days
            sameday = st + weeks*week
            assert sameday <= en < sameday + week
            
            # number of days remaining
            days = (en - sameday).days
            if sameday.weekday() > en.weekday():
                # don't count weekend days in between
                days -= 2
            
            days += 1 # count both start and end days
            result = "%.1f" % ((weeks*5 + days)/10.0)
    
    return HttpResponse(result, content_type='text/plain;charset=utf-8')

@requires_role(["FUND", "TAAD", "GRAD"])
def new_account(request):
    accountform = AccountForm(request.POST or None)
    #This restricts a user to only creating account for a unit to which they belong.
    accountform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        if accountform.is_valid():
            account = accountform.save()
            messages.success(request, 'Created account ' + str(account.account_number))
            l = LogEntry(userid=request.user.username,
            description="Created account %s" % (str(account.account_number)),
            related_object=account)
            l.save()    
            return HttpResponseRedirect(reverse('ra:accounts_index'))
    return render(request, 'ra/new_account.html', {'accountform': accountform})

@requires_role("FUND")
def edit_account(request, account_slug):
    account = get_object_or_404(Account, slug=account_slug, unit__in=request.units)
    if request.method == 'POST':
        accountform = AccountForm(request.POST, instance=account)
        if accountform.is_valid():
            accountform.save()
            messages.success(request, 'Updated account ' + str(account.account_number))
            l = LogEntry(userid=request.user.username,
            description="Updated account %s" % (str(account.account_number)),
            related_object=account)
            l.save()
            return HttpResponseRedirect(reverse('ra:accounts_index'))
    else:
        accountform = AccountForm(instance=account)
        accountform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    return render(request, 'ra/edit_account.html', {'accountform': accountform, 'account': account})

@requires_role("FUND")
def remove_account(request, account_slug):
    account = get_object_or_404(Account, slug=account_slug, unit__in=request.units)
    account.delete()
    messages.success(request, "Removed account %s." % str(account.account_number))
    l = LogEntry(userid=request.user.username,
          description="Removed account %s" % (str(account.account_number)),
          related_object=account)
    l.save()              
    return HttpResponseRedirect(reverse('ra:accounts_index'))

@requires_role("FUND")
def accounts_index(request):
    accounts = Account.objects.filter(unit__in=request.units, hidden=False).order_by("account_number")
    return render(request, 'ra/accounts_index.html', {'accounts': accounts})
