from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Letter
from django.template.base import Template
from django.template.context import Context
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from grad.forms import LetterEmailForm
from django.core.mail import EmailMultiAlternatives
from coredata.models import Person


def timezone_today():
    """
    Return the timezone-aware version of datetime.date.today()
    """
    # field default must be a callable (so it's the "today" of the request, not the "today" of the server startup)
    return timezone.now().date().isoformat()

@requires_role("GRAD")
def send_letter_email(request, grad_slug, letter_slug):
    letter = get_object_or_404(Letter, slug=letter_slug)
    grad = get_object_or_404(GradStudent, person=letter.student.person, slug=grad_slug, program__unit__in=request.units)
    if request.method == 'POST':
        form = LetterEmailForm(request.POST)
        if form.is_valid():
            letter.set_email_body(form.cleaned_data['email_body'])
            letter.set_email_subject(form.cleaned_data['email_subject'])
            if 'email_cc' in form.cleaned_data:
                letter.set_email_cc(form.cleaned_data['email_cc'])
            letter.set_email_sent(timezone_today())
            letter.save()
            return _send_letter(request, grad_slug, letter)

    else:
        email_template = letter.template.email_body()
        temp = Template(email_template)
        ls = grad.letter_info()
        text = temp.render(Context(ls))
        form = LetterEmailForm(initial={'email_body': text, 'email_subject': letter.template.email_subject()})
    return render(request, 'grad/select_letter_email_text.html', {'form': form, 'grad': grad, 'letter': letter})


@requires_role("GRAD")
def _send_letter(request, grad_slug, letter):
    from .get_letter import get_letter
    grad = get_object_or_404(GradStudent, person=letter.student.person, slug=grad_slug, program__unit__in=request.units)
    letter_attachment = get_letter(request, grad_slug, letter.slug)
    sender = Person.objects.get(userid=request.user.username)
    filename = letter.template.label.replace(' ', '_')
    from_email = sender.email()
    if letter.email_cc():
        email_cc = [from_email + ', ' + letter.email_cc()]
    else:
        email_cc = [from_email]
    if grad.applic_email():
        to_email = grad.applic_email()
    else:
        to_email = grad.person.email()
    msg = EmailMultiAlternatives(letter.email_subject(), letter.email_body(), from_email,
                                 [to_email], headers={'X-coursys-topic': 'grad'}, cc=email_cc)
    msg.attach(('%s.pdf' % filename), letter_attachment.getvalue(), 'application/pdf')
    msg.send()
    messages.add_message(request,
                         messages.SUCCESS,
                         'Email was sent')
    l = LogEntry(userid=request.user.username,
                 description="Send email from letter %s to %s" % (letter.slug, grad_slug),
                 related_object=letter)
    l.save()
    return HttpResponseRedirect(reverse('grad:manage_letters', kwargs={'grad_slug': grad_slug}))
