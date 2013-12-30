from courselib.auth import requires_role
from django.shortcuts import get_object_or_404
from grad.models import GradStudent, LetterTemplate
from django.template.base import Template
from django.template.context import Context
from django.http import HttpResponse

@requires_role("GRAD", get_only=["GRPD"])
def get_letter_text(request, grad_slug, letter_template_id):
    """ Get the text from letter template """
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    lt = get_object_or_404(LetterTemplate, id=letter_template_id, unit__in=request.units)
    temp = Template(lt.content)
    ls = grad.letter_info()
    text = temp.render(Context(ls))
    #print ls

    return HttpResponse(text, content_type='text/plain')
