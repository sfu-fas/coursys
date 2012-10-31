from courselib.auth import requires_role
from django.shortcuts import get_object_or_404
from grad.models import Letter
from django.http import HttpResponse
from dashboard.letters import OfficialLetter, LetterContents

@requires_role("GRAD", get_only=["GRPD"])
def get_letter(request, grad_slug, letter_slug):
    letter = get_object_or_404(Letter, slug=letter_slug, student__slug=grad_slug, student__program__unit__in=request.units)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=%s.pdf' % (letter_slug)

    doc = OfficialLetter(response, unit=letter.student.program.unit)
    l = LetterContents(to_addr_lines=letter.to_lines.split("\n"), 
                        from_name_lines=letter.from_lines.split("\n"), 
                        date=letter.date, 
                        salutation=letter.salutation,
                        closing=letter.closing, 
                        signer=letter.from_person,
                        use_sig=letter.use_sig())
    content_lines = letter.content.split("\n\n")
    l.add_paragraphs(content_lines)
    doc.add_letter(l)
    doc.write() 
    return response
