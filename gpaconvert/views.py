import decimal
import functools

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.template import RequestContext, loader
from django.forms.formsets import formset_factory
from django.contrib import messages

from courselib.auth import requires_global_role

from gpaconvert.models import GradeSource
from gpaconvert.models import UserArchive
from gpaconvert.forms import ContinuousGradeForm
from gpaconvert.forms import DiscreteGradeForm
from gpaconvert.forms import GradeSourceListForm
from gpaconvert.utils import render_to
from gpaconvert.forms import GradeSourceForm
from gpaconvert.forms import GradeSourceChangeForm
from gpaconvert.forms import rule_formset_factory

import random
import hashlib
import datetime

# admin interface views

@requires_global_role('GPA')
@render_to('gpaconvert/admin_base.html')
def grade_sources(request):
    # Get list of grade sources
    grade_sources = GradeSource.objects.active()
    if request.GET.get("show_deleted") == '1':
        grade_sources = GradeSource.objects.all()
    data = {'grade_sources': grade_sources}
    return data


@render_to('gpaconvert/new_grade_source.html')
@requires_global_role('GPA')
def new_grade_source(request):
    data = {"grade_source_form": GradeSourceForm()}
    if request.method == "POST":
        form = GradeSourceForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            return HttpResponseRedirect(reverse('grade_source_index'))
        else:
            messages.error(request, "Please correct the error below")
            form = GradeSourceForm(form.data)
            data.update({
                "grade_source_form": form,
            })
    return data


@render_to('gpaconvert/change_grade_source.html')
@requires_global_role('GPA')
def change_grade_source(request, slug):
    grade_source = get_object_or_404(GradeSource, slug__exact=slug)
    old_scale = grade_source.scale
    ChangeForm = GradeSourceChangeForm

    # Prep formset
    # If the formset is of continuous rules and the first entry is empty
    # populate the first entry with a default lower bound '0'
    formset = rule_formset_factory(grade_source)
    if formset.initial_form_count() == 0:
        formset[0].initial.update({"lookup_lbound": 0})
    data = {
        "grade_source_form": ChangeForm(instance=grade_source),
        "rule_formset": formset,
        "grade_source": grade_source
    }

    if request.method == "POST":
        form = ChangeForm(request.POST, instance=grade_source)
        if form.is_valid():
            grade_source = form.save(commit=False)
            # ---------------------------
            # Do any post processing here
            # ---------------------------
            grade_source.save()
            data.update({
                "grade_source": grade_source,
                "grade_source_form": ChangeForm(instance=grade_source),
                "rule_formset": rule_formset_factory(grade_source),
            })
        else:
            form = ChangeForm(form.data, instance=grade_source)
            data.update({
                "grade_source_form": form,
            })
            return data

        if grade_source.scale != old_scale:
            return HttpResponseRedirect(reverse('change_grade_source', args=[grade_source.slug]))
        # Handle conversion rule formsets
        formset = rule_formset_factory(grade_source, request.POST)
        if formset.is_valid():
            formset.save()
        else:
            formset = rule_formset_factory(grade_source, formset.data)
            data.update({
                "rule_formset": formset,
            })
            return data
    return data
        

# user interface views

@render_to('gpaconvert/grade_source_list.html')
def list_grade_sources(request):
    form = GradeSourceListForm(request.GET)
    country = request.GET.get('country', None)
    grade_sources = GradeSource.objects.filter(status='ACTI')

    if country:
        grade_sources = grade_sources.filter(country=country)

    return {
        'form': form,
        'grade_sources': grade_sources,
    }


def get_transfer_rules(formset):
    transfer_rules = []
    transfer_grade_points = decimal.Decimal('0.00')
    transfer_credits = decimal.Decimal('0.00')
    # XXX: Not able to use form.is_valid() here because formset.is_valid() seems to cause
    #      that to return True for all forms.
    for form in formset:
        if 'rule' in form.cleaned_data:
            transfer_rules.append(form.cleaned_data['rule'])
            credits = form.cleaned_data['credits']
            transfer_grade_points += credits * transfer_rules[-1].grade_points
            transfer_credits += credits
        else:
            transfer_rules.append(None)
    return transfer_rules, transfer_grade_points, transfer_credits

@render_to('gpaconvert/convert_grades_form.html')
def convert_grades(request, grade_source_slug):
    grade_source = get_object_or_404(GradeSource, slug=grade_source_slug)
    RuleForm = (grade_source.scale == 'DISC') and DiscreteGradeForm or ContinuousGradeForm

    # XXX: This is required because our form class requires a GradeSource.
    RuleFormSet = formset_factory(RuleForm, extra=10)
    RuleFormSet.form = functools.partial(RuleForm, grade_source=grade_source)

    transfer_rules = []
    transfer_grade_points = decimal.Decimal('0.00')
    transfer_credits = decimal.Decimal('0.00')

    if request.POST:
        formset = RuleFormSet(request.POST)
        formset.is_valid()
        transfer_rules, transfer_grade_points, transfer_credits = get_transfer_rules(formset)

        # Save the data for later
        if request.POST.get("save_grades"):
            data = formset.data
            salt = hashlib.sha224(str(random.random())).hexdigest()[:5]
            key = hashlib.sha224(salt+grade_source_slug+str(datetime.datetime.now())).hexdigest()
            arch = UserArchive.objects.create(grade_source=grade_source, slug=key, data=data)
            return HttpResponseRedirect(arch.get_absolute_url())


    else:
        formset = RuleFormSet()
        transfer_rules = [None for _ in formset]

    if transfer_credits > 0:
        transfer_gpa = transfer_grade_points / transfer_credits
    else:
        transfer_gpa = decimal.Decimal('0.00')

    return {
        'grade_source': grade_source,
        'formset': formset,
        'transfer_rules': iter(transfer_rules),
        'transfer_gpa': transfer_gpa,
    }


@render_to('gpaconvert/convert_grades_form.html')
def view_saved(request, grade_source_slug, slug):
    arch = get_object_or_404(UserArchive, slug=slug)
    grade_source = arch.grade_source
    RuleForm = (grade_source.scale == 'DISC') and DiscreteGradeForm or ContinuousGradeForm
    
    RuleFormSet = formset_factory(RuleForm, extra=10)
    RuleFormSet.form = functools.partial(RuleForm, grade_source=grade_source)
    formset = RuleFormSet(arch.data)

    formset.is_valid()
    transfer_rules, transfer_grade_points, transfer_credits = get_transfer_rules(formset)
    if transfer_credits > 0:
        transfer_gpa = transfer_grade_points / transfer_credits
    else:
        transfer_gpa = decimal.Decimal('0.00')

    return {
        'grade_source': grade_source,
        'formset': formset,
        'transfer_rules': iter(transfer_rules),
        'transfer_gpa': transfer_gpa
    }
