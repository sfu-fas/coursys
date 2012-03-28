from celery.task import task
from grad.forms import process_pcs_export
from django.core.mail import send_mail
from django.conf import settings

@task(rate_limit="1/m", max_retries=2)
def process_pcs_task(data, email):
    msg = process_pcs_export(data)
    send_mail(subject="PCS Import Results", message=msg, from_email=email, recipient_list=[email], fail_silently=False)

#process_pcs_export(data)