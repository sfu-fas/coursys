from django.db import models

from event_types.career import AppointmentEventHandler, SalaryBaseEventHandler

EVENT_TYPES = { # dictionary of CareerEvent.event_type value -> CareerEventManager class
        'APPOINT': AppointmentEventHandler,
        'SALARY': SalaryBaseEventHandler,
        }

class CareerEvent(models.Model):
    # ...

    def save(self, editor, *args, **kwargs):
        assert editor.__class__.__name__ == 'Person' # we're doing to so we can add an audit trail later.

        res = super(CareerEvent, self).save(*args, **kwargs)
        return res


class DocumentAttachment(models.Model):
    """
    Document attached to a CareerEvent.
    """
    pass


class MemoTemplate(models.Model):
    """
    A template for memos.
    """
    pass


class Memo(models.Model):
    """
    A memo created by the system, and attached to a CareerEvent.
    """
    pass


