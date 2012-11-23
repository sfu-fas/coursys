from onlineforms.models import Field, SheetSubmissionSecretUrl
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives

ORDER_TYPE = {'UP': 'up', 'DN': 'down'}

def reorder_sheet_fields(ordered_fields, field_slug, order):
    """
    Reorder the activity in the field list of a course according to the
    specified order action. Please make sure the field list belongs to
    the same sheet.
    """
    for field in ordered_fields:
        if not isinstance(field, Field):
            raise TypeError(u'ordered_fields should be list of Field')
    for i in range(0, len(ordered_fields)):
        if ordered_fields[i].slug == field_slug:
            if (order == ORDER_TYPE['UP']) and (not i == 0):
                # swap order
                temp = ordered_fields[i-1].order
                ordered_fields[i-1].order = ordered_fields[i].order
                ordered_fields[i].order = temp
                ordered_fields[i-1].save()
                ordered_fields[i].save()
            elif (order == ORDER_TYPE['DN']) and (not i == len(ordered_fields) - 1):
                # swap order
                temp = ordered_fields[i+1].order
                ordered_fields[i+1].order = ordered_fields[i].order
                ordered_fields[i].order = temp
                ordered_fields[i+1].save()
                ordered_fields[i].save()
            break


def get_sheet_submission_url(sheet_submission):
    """
    Creates a URL for a sheet submission.
    If a secret URL has been generated it will use that,
    otherwise it will create a standard URL.
    """
    secret_urls = SheetSubmissionSecretUrl.objects.filter(sheet_submission=sheet_submission)
    if secret_urls:
        return reverse('onlineforms.views.sheet_submission_via_url', kwargs={'secret_url': secret_urls[0].key})
    else:
        return reverse('onlineforms.views.sheet_submission', kwargs={
                                'form_slug': sheet_submission.form_submission.form.slug,
                                'formsubmit_slug': sheet_submission.form_submission.slug,
                                'sheet_slug': sheet_submission.sheet.slug,
                                'sheetsubmit_slug': sheet_submission.slug})


def email_assigned(request, admin, assignee, sheet_submission):
    plaintext = get_template('onlineforms/emails/email.txt')
    htmly = get_template('onlineforms/emails/email.html')

    full_url = request.build_absolute_uri(get_sheet_submission_url(sheet_submission))
    email_context = Context({'username': admin.name(), 'assignee': assignee.name(), 'sheeturl': full_url})
    subject, from_email, to = 'CourSys: You have been assigned a sheet to complete.', "nobody@courses.cs.sfu.ca", assignee.full_email()
    msg = EmailMultiAlternatives(subject, plaintext.render(email_context), from_email, [to])
    msg.attach_alternative(htmly.render(email_context), "text/html")
    msg.send()


def email_nonsfu_initialized(sheet_submission):
    pass
