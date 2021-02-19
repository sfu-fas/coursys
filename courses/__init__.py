# per https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html
from .celery import app as celery_app
__all__ = ('celery_app',)