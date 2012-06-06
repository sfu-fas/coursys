from courselib.auth import requires_role
from django.shortcuts import get_object_or_404
from grad.models import Letter
from django.http import HttpResponse
from dashboard.letters import OfficialLetter, LetterContents

from pages.models import _normalize_newlines
@requires_role("GRAD")
def get_letter(request, letter_slug):
    letter = get_object_or_404(Letter, slug=letter_slug, student__program__unit__in=request.units)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=%s.pdf' % (letter_slug)

    doc = OfficialLetter(response, unit=letter.student.program.unit)
    l = LetterContents(to_addr_lines=letter.to_lines.split("\n"), 
                        from_name_lines=letter.from_lines.split("\n"), 
                        date=letter.date, 
                        salutation=letter.salutation,
                        closing=letter.closing, 
                        signer=letter.from_person)
    content_text = _normalize_newlines(letter.content.rstrip())
    content_lines = content_text.split("\n\n")
    l.add_paragraphs(content_lines)
    doc.add_letter(l)
    doc.write() 
    return response
