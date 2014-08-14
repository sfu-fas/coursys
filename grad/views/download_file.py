from courselib.auth import requires_role
from django.shortcuts import get_object_or_404
from grad.models import ExternalDocument
from django.http import HttpResponse

@requires_role("GRAD", get_only=["GRPD"])
def download_file(request, grad_slug, d_id):
    # we don't actually need the grad slug. 
    document = get_object_or_404(ExternalDocument, 
                                 id=d_id, 
                                 student__program__unit__in=request.units)
    document.file_attachment.open()
    resp = HttpResponse(document.file_attachment, 
                        content_type=document.file_mediatype)
    resp['Content-Disposition'] = ('inline; filename="' + 
                                   document.attachment_filename() + '"')
    return resp
