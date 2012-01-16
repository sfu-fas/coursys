from django.http import HttpResponse
from courselib.auth import requires_course_staff_by_slug, is_course_staff_by_slug, is_course_student_by_slug, ForbiddenResponse, NotFoundResponse

@requires_course_staff_by_slug
def index_page(request, course_slug):
    if is_course_staff_by_slug(request, course_slug):
        return HttpResponse('TUGs index')
    else:
        return ForbiddenResponse(request)
        
@requires_course_staff_by_slug
def all_tugs(request, course_slug):
    return HttpResponse('All TUGs page')

@requires_course_staff_by_slug    
def new_tug(request, course_slug):
    return HttpResponse('New TUG page')

@requires_course_staff_by_slug    
def view_tug(request, course_slug, userid):
    return HttpResponse('View TUG page')

@requires_course_staff_by_slug
def edit_tug(request, course_slug, userid):
    return HttpResponse('Edit TUG page')
