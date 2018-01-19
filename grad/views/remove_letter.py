from courselib.auth import requires_role
from django.shortcuts import get_object_or_404
from grad.models import Letter, GradStudent
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import requires_role
from django.http import HttpResponseRedirect
from django.urls import reverse


@requires_role("GRAD")
def remove_letter(request, grad_slug, letter_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    letter = Letter.objects.get(student=grad, slug=letter_slug)
    if request.method == 'POST':
        letter.removed = True
        letter.save()

    messages.success(request, "Letter removed.")
    l = LogEntry(userid=request.user.username,
                 description="Removed letter for %s." % grad.person.userid,
                 related_object=letter)
    l.save()

    return HttpResponseRedirect(reverse('grad:manage_letters', kwargs={'grad_slug': grad_slug}))
