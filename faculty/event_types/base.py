from django import forms
from coredata.models import Role
import datetime

PERMISSION_CHOICES = { # who can create/edit/approve various things?
        'MEMB': 'Faculty Member',
        'DEPT': 'Department',
        'FAC': 'Dean\'s Office',
        }
PERMISSION_LEVEL = {
        'MEMB': 0,
        'DEPT': 1,
        'FAC': 2,
        }

class BaseEntryForm(forms.Form):
    # TODO: should this be a ModelForm for a CareerEvent? We'll have a circular import if so.
    title = forms.CharField(max_length=80, required=True)
    start_date = forms.DateField()
    end_date = forms.DateField()
    


class CareerEventType(object):
    is_instant = False # set to True for events that have no duration
    exclusion_category = None # if set, only one CareerEvent with this exclusion_category
                              # can exist for a facuty member at a given time.
    editable_by = 'DEPT'
    approval_by = 'FAC'
    
    def __init__(self, faculty):
        """
        faculty: a coredata.Person representing the faculty member in question.
        """
        self.faculty = faculty


    def permission(self, editor):
        """
        This editor's permission level with respect to this faculty member.
        """
        edit_units = set(r.unit for r in Role.objects.filter(person=editor, role='ADMN'))
        fac_units = set(r.unit for r in Role.objects.filter(person=self.faculty, role='FAC'))

        if editor == faculty:
            # first on purpose: don't let dept chairs approve/edit their own stuff
            return 'MEM'

        elif False: # TODO: detect faculty-level permission
            return 'FAC'

        elif edit_units & fac_units:
            return 'DEPT'

        
    def has_permission(self, perm, editor):
        """
        Does the given editor (a coredata.Person) have this permission
        for this faculty member?
        
        Implemented as a method so we can override or extend if necessary.
        """
        permission = self.permission(editor)
        return PERMISSION_LEVEL[permission] >= PERMISSION_LEVEL[perm]

    def can_edit(self, editor):
        """
        Can the given editor (a coredata.Person) can create/edit this
        CareerEventType for this faculty member?
        """
        return self.has_permission(self.editable_by, editor)
            
    def can_approve(self, editor):
        """
        Can the given editor (a coredata.Person) can approve this
        CareerEventType for this faculty member?
        """
        return self.has_permission(self.approval_by, editor, faculty)
            
    
    #class EntryForm(BaseEntryForm):
    #    pass

    def default_title(self):
        return 'Some Career Event'

    def get_entry_form(self, event=None):
        """
        Return a Django Form that can be used to create/edit a CareerEvent
        """
        initial = {'title': self.default_title(), 'start_date': datetime.date.today()}
        f = self.EntryForm(initial=initial)

        if self.is_instant and 'end_date' in f.fields:
            del f.fields['end_date']

        return f

    
    def to_career_event(self, form):
        """
        Given an EntryForm instance, return the corresponding CareerEvent instance
        (~= inverse of get_entry_form)
        """
        raise NotImplementedError
    
    
