import decimal
import functools

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.forms.formsets import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

from courselib.auth import requires_global_role, has_role
from dashboard.models import new_feed_token
from log.models import LogEntry

from gpaconvert.forms import ContinuousGradeForm
from gpaconvert.forms import DiscreteGradeForm
from gpaconvert.forms import GradeSourceChangeForm
from gpaconvert.forms import GradeSourceForm
from gpaconvert.forms import GradeSourceListForm
from gpaconvert.forms import rule_formset_factory
from gpaconvert.models import GradeSource
from gpaconvert.models import UserArchive
from gpaconvert.utils import render_to


# admin interface views

@requires_global_role('GPA')
@render_to('gpaconvert/admin_base.html')
def grade_sources(request):
    # Get list of grade sources
    grade_sources = GradeSource.objects.active()
    if request.GET.get("show_deleted") == '1':
        grade_sources = GradeSource.objects.all()

    return {
        'grade_sources': grade_sources,
    }


@requires_global_role('GPA')
@render_to('gpaconvert/new_grade_source.html')
def new_grade_source(request):
    data = {
        "grade_source_form": GradeSourceForm(),
    }

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


@requires_global_role('GPA')
@render_to('gpaconvert/change_grade_source.html')
def change_grade_source(request, slug):
    grade_source = get_object_or_404(GradeSource, slug__exact=slug)
    old_scale = grade_source.scale

    # Prep formset
    # If the formset is of continuous rules and the first entry is empty
    # populate the first entry with a default lower bound '0'
    formset = rule_formset_factory(grade_source)
    if formset.initial_form_count() == 0:
        formset[0].initial.update({"lookup_lbound": 0})

    data = {
        "grade_source_form": GradeSourceChangeForm(instance=grade_source),
        "rule_formset": formset,
        "grade_source": grade_source,
    }

    if request.method == "POST":
        form = GradeSourceChangeForm(request.POST, instance=grade_source)
        if form.is_valid():
            grade_source = form.save(commit=False)
            grade_source.save()
            data.update({
                "grade_source": grade_source,
                "grade_source_form": GradeSourceChangeForm(instance=grade_source),
                "rule_formset": rule_formset_factory(grade_source),
            })
        else:
            data['form'] = GradeSourceChangeForm(form.data, instance=grade_source)
            return data

        if grade_source.scale != old_scale:
            return HttpResponseRedirect(reverse('change_grade_source', args=[grade_source.slug]))

        # Handle conversion rule formsets
        formset = rule_formset_factory(grade_source, request.POST)
        if formset.is_valid():
            formset.save()
        else:
            formset = rule_formset_factory(grade_source, formset.data)
            data['rule_formset'] = formset
            return data

    return data


# user interface views

@render_to('gpaconvert/grade_source_list.html')
def list_grade_sources(request):
    form = GradeSourceListForm(request.GET)
    country = request.GET.get('country', None)
    grade_sources = GradeSource.objects.filter(status='ACTI')
    is_admin = has_role('GPA', request)

    if country:
        grade_sources = grade_sources.filter(country=country)

    return {
        'form': form,
        'grade_sources': grade_sources,
        'is_admin': is_admin,
    }


def _get_transfer_rules(formset):
    transfer_rules = []
    transfer_grade_points = decimal.Decimal('0.00')
    transfer_credits = decimal.Decimal('0.00')
    secondary_grade_points = decimal.Decimal('0.00')
    secondary_credits = decimal.Decimal('0.00')

    for form in formset:
        # XXX: Not able to use form.is_valid() here because formset.is_valid() seems to cause
        #      that to return True for all forms.
        if ('rule' in form.cleaned_data) and ('credits' in form.cleaned_data):
            transfer_rules.append(form.cleaned_data['rule'])
            credits = form.cleaned_data['credits']
            transfer_grade_points += credits * transfer_rules[-1].grade_points
            transfer_credits += credits
            if form.cleaned_data['include_secondary_gpa']:
                secondary_grade_points += credits * transfer_rules[-1].grade_points
                secondary_credits += credits
        else:
            transfer_rules.append(None)

    return transfer_rules, transfer_grade_points, transfer_credits, secondary_grade_points, secondary_credits


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
    secondary_grade_points = decimal.Decimal('0.00')
    secondary_credits = decimal.Decimal('0.00')

    if request.POST:
        formset = RuleFormSet(request.POST)
        if not formset.is_valid():
            messages.error(request, "Please correct the error below")

        # Save the data for later
        if request.POST.get("save_grades"):
            key = new_feed_token()
            arch = UserArchive.objects.create(grade_source=grade_source, slug=key, data=formset.data)
            url = arch.get_absolute_url()

            # Log that a save happened
            LogEntry.objects.create(userid=request.user.username,
                                    description="saved GPA calculation from {} {}".format(grade_source, key),
                                    related_object=arch)

            message = ('Grade conversion saved. You can share this URL if you want others to see these grades: {}'
                       .format(request.build_absolute_uri(url)))
            messages.add_message(request, messages.SUCCESS, message)
            return HttpResponseRedirect(url)
        else:
            tmp = _get_transfer_rules(formset)
            transfer_rules, transfer_grade_points, transfer_credits, secondary_grade_points, secondary_credits = tmp
    else:
        formset = RuleFormSet()
        transfer_rules = [None for _ in formset]

    if transfer_credits > 0:
        transfer_gpa = transfer_grade_points / transfer_credits
    else:
        transfer_gpa = None

    if secondary_credits > 0:
        secondary_gpa = secondary_grade_points / secondary_credits
    else:
        secondary_gpa = None

    return {
        'grade_source': grade_source,
        'formset': formset,
        'transfer_rules': iter(transfer_rules),
        'transfer_gpa': transfer_gpa,
        'secondary_gpa': secondary_gpa,
    }


@render_to('gpaconvert/convert_grades_form.html')
def view_saved(request, grade_source_slug, slug):
    arch = get_object_or_404(UserArchive, grade_source__slug=grade_source_slug, slug=slug)
    grade_source = arch.grade_source
    RuleForm = (grade_source.scale == 'DISC') and DiscreteGradeForm or ContinuousGradeForm

    RuleFormSet = formset_factory(RuleForm, extra=10)
    RuleFormSet.form = functools.partial(RuleForm, grade_source=grade_source)
    formset = RuleFormSet(arch.data)

    formset.is_valid()
    tmp = _get_transfer_rules(formset)
    transfer_rules, transfer_grade_points, transfer_credits, secondary_grade_points, secondary_credits = tmp

    if transfer_credits > 0:
        transfer_gpa = transfer_grade_points / transfer_credits
    else:
        transfer_gpa = None

    if secondary_credits > 0:
        secondary_gpa = secondary_grade_points / secondary_credits
    else:
        secondary_gpa = None

    return {
        'grade_source': grade_source,
        'formset': formset,
        'transfer_rules': iter(transfer_rules),
        'transfer_gpa': transfer_gpa,
        'secondary_gpa': secondary_gpa,
    }
