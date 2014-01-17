from django.db import models

from event_types.career import AppointmentEventType
EVENT_TYPES = {
        'APPOINT': AppointmentEventType,
        }

class CareerEvent(models.Model):
    # ...

    def save(self, editor, *args, **kwargs):
        assert editor.__class__.__name__ == 'Person' # we're doing to so we can add an audit trail later.

        res = super(CareerEvent, self).save(*args, **kwargs)
        return res
