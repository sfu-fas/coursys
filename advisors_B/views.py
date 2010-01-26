# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import Context, loader
from advisors_B.models import *
#from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from courselib.auth import requires_advisor
from django.template import RequestContext
from coredata.models import Member
from datetime import datetime
from django.core.files.uploadedfile import SimpleUploadedFile

@requires_advisor()
def index(request):
    is_advisor = True
    for advisor in Role.objects.filter(role = 'ADVS'):
        if advisor.person.userid == request.user.username:
            is_advisor = True
            break
    if is_advisor:
        return render_to_response("advisors_B/advisor.html", context_instance=RequestContext(request))
    else:
        note_list = Note.objects.filter(student__userid = request.user.username).order_by('-create_date')
        print note_list
        return render_to_response("advisors_B/student.html",{'note_list':note_list}, context_instance=RequestContext(request))

@requires_advisor()
def search_result(request):
    error=False
    if 'q' in request.GET:
        q=request.GET['q']
        if not q:
            error=True
        else:
            qstr=(Q(first_name__icontains = q)|
		Q(last_name__icontains = q) |
		Q(middle_name__icontains = q))
            students=Person.objects.filter(qstr)
            return render_to_response('search_result.html',{'students':students,'q':q})
     #return render_to_response('search_form.html',{'error',error})
#use the example code in the book <<The definitive guide to Django>>,chapt.7

@requires_advisor()
def search_form(request):
    return render_to_response('search_form.html')


@login_required()
def create(request, advisor_id, student_id):
    p = Person.objects.get(userid = advisor_id)
    advisor = Role.objects.get(person = p)
    student = Person.objects.get(userid = student_id)
    return render_to_response("advisors_B/create.html", {'advisor':advisor, 'student': student})

@login_required
def detail(request, note_id):
    try:
        n = Note.objects.get(pk = note_id)
    except Note.DoesNotExist:
        raise Http404
    return render_to_response("advisors_B/detail.html",{'note':n})

@login_required
def submit(request, advisor_id, student_id):
	p = get_object_or_404(Person, userid = advisor_id)
	a = get_object_or_404(Role, person = p)
	s = get_object_or_404(Person, userid = student_id)
	con = request.POST['NoteContent']
	f = request.FILES.get('browns')
	try:
		hid = request.POST['hide']
	except KeyError:
		hid = False
	n = Note(content = con, student = s, create_date = datetime.now(), author = a, hidden = hid, file = f)
	n.save();
	return render_to_response('advisors_B/succeed.html', {'create_date':datetime.now(), 'advisor_id':advisor_id}) # Redirect after POST
