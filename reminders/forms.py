from .models import Reminder
from django import forms
from coredata.models import Unit, Course, CourseOffering, Member

from courselib.markup import MarkupContentMixin, MarkupContentField
import datetime

class ReminderForm(MarkupContentMixin(), forms.ModelForm):
    content = MarkupContentField()
    
    def __init__(self, person, *args, **kwargs):
        cutoff = datetime.date.today() - datetime.timedelta(days=365)
        instructors = Member.objects.filter(role='INST', person=person, offering__semester__end__gt=cutoff).select_related('offering__course')
        courses = {m.offering.course for m in instructors}
        courses = sorted(list(courses))
        course_choices = [(c.id, str(c)) for c in courses]

        super().__init__(*args, **kwargs)
        self.fields['course'].choices = [(None, '—')] + course_choices

    class Meta:
        model = Reminder
        exclude = ['person', 'config', 'status']
        widgets = {
            'reminder_type': forms.RadioSelect,
            'date_type': forms.RadioSelect,
        }
