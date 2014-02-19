from celery.task import task
from grad.forms import process_pcs_export
from django.core.mail import send_mail
from django.conf import settings

@task(rate_limit="1/m", max_retries=2)
def XXX_process_pcs_task(data, unit_id, semester_id, user):
    msg = process_pcs_export(data, unit_id, semester_id, user)
    send_mail(subject="PCS Import Results", message=msg, from_email=user.email(), recipient_list=[user.email()], fail_silently=False)

#process_pcs_export(data)