from planning.models import TeachingCapability, TeachingIntention
from courselib.auth import requires_instructor
from coredata.models import Person
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext


@requires_instructor
def instructor_index(request):
    instructor = get_object_or_404(Person, userid=request.user.username)
    capability_list = TeachingCapability.objects.filter(instructor=instructor).order_by('course')
    intention_list = TeachingIntention.objects.filter(instructor=instructor).order_by('semester')

    return render_to_response("planning/instructor_index.html", {'capability_list': capability_list, 'intention_list': intention_list}, context_instance=RequestContext(request))
