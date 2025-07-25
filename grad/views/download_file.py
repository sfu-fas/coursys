from courselib.auth import requires_role
from django.shortcuts import get_object_or_404
from grad.models import ExternalDocument
from django.http import HttpResponse
from courselib.auth import ForbiddenResponse
from django.contrib.auth.decorators import login_required
from grad.views.view import _can_view_student

@login_required
def download_file(request, grad_slug, d_id):
    grad, authtype, units = _can_view_student(request, grad_slug)
    if grad is None or authtype == 'student':
        return ForbiddenResponse(request)
    document = get_object_or_404(ExternalDocument, 
                                 id=d_id, 
                                 student=grad,
                                 student__program__unit__in=units)
    document.file_attachment.open()
    resp = HttpResponse(document.file_attachment, 
                        content_type=document.file_mediatype)
    resp['Content-Disposition'] = ('inline; filename="' + 
                                   document.attachment_filename() + '"')
    return resp
