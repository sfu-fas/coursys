from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import RequestContext, loader
from django.core.urlresolvers import reverse

from models import GradeSource
from forms import GradeSourceForm
from forms import rule_formset_factory


def grade_sources(request):
    t = loader.get_template('gpaconvert/admin_base.html')
    
    # Get list of grade sources
    grade_sources = GradeSource.objects.active()
    if request.GET.get("show_deleted") == '1':
        grade_sources = GradeSource.objects.all()
    data = {'grade_sources' : grade_sources}
    c = RequestContext(request, data)
    return HttpResponse(t.render(c))


def new_grade_source(request):
    t = loader.get_template('gpaconvert/new_grade_source.html')
    data = {"grade_source_form" : GradeSourceForm()}
    if request.method == "POST":
        form = GradeSourceForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            print instance
            return HttpResponseRedirect(reverse('grade_source_index'))
        else:
            form = GradeSourceForm(form.data)
            c = RequestContext(request, data)
            return HttpResponse(t.render(c))

    c = RequestContext(request, data)
    return HttpResponse(t.render(c))


def change_grade_source(request, slug):
    t = loader.get_template('gpaconvert/change_grade_source.html')
    grade_source = get_object_or_404(GradeSource, slug__exact=slug)
    old_scale = grade_source.scale
    data = {"grade_source_form" : GradeSourceForm(instance=grade_source),
            "rule_formset" : rule_formset_factory(grade_source),
            "grade_source" : grade_source}

    if request.method == "POST":
        form = GradeSourceForm(request.POST, instance=grade_source)
        if form.is_valid():
            grade_source = form.save(commit=False)
            # ---------------------------
            # Do any post processing here
            # ---------------------------
            grade_source.save()
            data.update({"grade_source": grade_source,
                         "grade_source_form" : GradeSourceForm(instance=grade_source)})
            #return HttpResponseRedirect(reverse("change_grade_source", args=[grade_source.slug]))
        
        else:
            form = GradeSourceForm(form.data, instance=grade_source)
            data.update({"grade_source_form" : form})
            c = RequestContext(request, data)
            return HttpResponse(t.render(c))

        if grade_source.scale != old_scale:
            return HttpResponseRedirect(reverse('change_grade_source', args=[grade_source.slug]))
        # Handle conversion rule formsets
        formset = rule_formset_factory(grade_source, request.POST)
        if formset.is_valid():
            formset.save()
        else:
            formset = rule_formset_factory(grade_source, data=formset.data)
            data.update({"rule_formset" : formset})
            c = RequestContext(request, data)
            return HttpResponse(t.render(c))

    c = RequestContext(request, data)
    return HttpResponse(t.render(c))
