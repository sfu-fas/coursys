# Create your views here.
from forms import GradeSourceForm
from django.http import HttpResponse
from django.template import RequestContext, loader

from models import GradeSource

def grade_source_index(request):
	data = {'gradesourceform' : GradeSourceForm(), 'gradesources': GradeSource.objects.all() }
	t = loader.get_template('gpaconvert/gpa_admin_base.html')
	c = RequestContext(request, data)
	return HttpResponse(t.render(c))
