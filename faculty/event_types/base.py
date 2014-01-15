from django import forms
from coredata.models import Role

PERMISSION_CHOICES = { # who can create/edit/approve various things?
        'MEM': 'Faculty Member',
        'DEPT': 'Department',
        'FAC': 'Dean\'s Office',
        }
PERMISSION_LEVEL = {
        'MEM': 0,
        'DEPT': 1,
        'FAC': 2,
        }


class CareerEventType(object):
    is_instant = False # set to True for events that have no duration
    exclusion_category = None # if set, only one CareerEvent with this exclusion_category
                              # can exist for a facuty member at a given time.
    editable_by = 'DEPT'
    approval_by = 'FAC'


    def permission(self, editor, faculty):
        """
        This editor's permission level with respect to this faculty member.
        """
        edit_units = set(r.unit for r in Role.objects.filter(person=editor, role='ADMN'))
        fac_units = set(r.unit for r in Role.objects.filter(person=faculty, role='FAC'))

        if editor == faculty:
            # first on purpose: don't let dept chairs approve/edit their own stuff
            return 'MEM'

        elif False: # TODO: detect faculty-level permission
            return 'FAC'

        elif edit_units & fac_units:
            return 'DEPT'

        
    def has_permission(self, perm, editor, faculty):
        """
        Does the given editor (a coredata.Person) have this permission
        for this faculty member (also a Person)?
        
        Implemented as a method so we can override or extend if necessary.
        """
        permission = self.permission(editor, faculty)
        return PERMISSION_LEVEL[permission] >= PERMISSION_LEVEL[perm]

    def can_edit(self, editor, faculty):
        """
        Can the given editor (a coredata.Person) can create/edit this
        CareerEventType for this faculty member (also a Person)?
        """
        return self.has_permission(self.editable_by, editor, faculty)
            
    def can_approve(self, editor, faculty):
        """
        Can the given editor (a coredata.Person) can approve this
        CareerEventType for this faculty member (also a Person)?
        """
        return self.has_permission(self.approval_by, editor, faculty)
            
    
    class EntryForm(forms.Form):
        pass


    def get_entry_form(self, event=None):
        """
        Return a Django Form that can be used to create/edit a CareerEvent
        """
        raise NotImplementedError

    
    def to_career_event(self, form):
        """
        Given an EntryForm instance, return the corresponding CareerEvent instance
        (~= inverse of get_entry_form)
        """
        raise NotImplementedError
    
    
