from django import forms
from coredata.models import Role
import datetime, itertools

PERMISSION_CHOICES = { # who can create/edit/approve various things?
        'MEMB': 'Faculty Member',
        'DEPT': 'Department',
        'FAC': 'Dean\'s Office',
        }
PERMISSION_LEVEL = {
        'NONE': 0,
        'MEMB': 1,
        'DEPT': 2,
        'FAC': 3,
        }


class BaseEntryForm(forms.Form):
    # TODO: should this be a ModelForm for a CareerEvent? We'll have a circular import if so.
    title = forms.CharField(max_length=80, required=True)
    start_date = forms.DateField()
    end_date = forms.DateField()


class CareerEventType(object):
    # type configuration stuff: override as necessary
    is_instant = False # set to True for events that have no duration
    exclusion_category = None # if set, only one CareerEvent with this exclusion_category
                              # can exist for a faculty member at a given time.
    date_bias = 'DATE' # or 'SEM': which interface widget should be presented to default in the form?
    affects_teaching = False # events of this type might affect teaching credits/load
    affects_salary = False   # events of this type might affect salary/pay

    viewable_by = 'MEMB'
    editable_by = 'DEPT'
    approval_by = 'FAC'
    
    
    # basic functionality: hopefully don't have to override
    
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
        super_units = set(itertools.chain(*(u.super_units() for u in fac_units)))

        if editor == self.faculty:
            # first on purpose: don't let dept chairs approve/edit their own stuff
            return 'MEMB'
        elif edit_units & super_units:
            # give dean's office level permission to anybody above in the hierarchy:
            # not technically correct, but correct in practice.
            return 'FAC'
        elif edit_units & fac_units:
            return 'DEPT'
        else:
            return 'NONE'

        
    def has_permission(self, perm, editor):
        """
        Does the given editor (a coredata.Person) have this permission
        for this faculty member?
        
        Implemented as a method so we can override or extend if necessary.
        """
        permission = self.permission(editor)
        return PERMISSION_LEVEL[permission] >= PERMISSION_LEVEL[perm]

    def can_view(self, editor):
        """
        Can the given user (a coredata.Person) can view the
        CareerEventType for this faculty member?
        """
        return self.has_permission(self.viewable_by, editor)
            
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
        return self.has_permission(self.approval_by, editor)
            

    # maybe override? Hopefully we can avoid and use this as-is.

    def get_entry_form(self, event=None):
        """
        Return a Django Form that can be used to create/edit a CareerEvent
        """
        initial = {'title': self.default_title(), 'start_date': datetime.date.today()}
        f = self.EntryForm(initial=initial)

        if self.is_instant and 'end_date' in f.fields:
            del f.fields['end_date']

        return f


    # type-specific stuff that probably need to be overridden.
    
    class EntryForm(BaseEntryForm):
        pass

    def default_title(self):
        return 'Some Career Event'

    def to_career_event(self, form):
        """
        Given an EntryForm instance, return the corresponding CareerEvent instance
        (~= inverse of get_entry_form)
        """
        # TODO: can we be general enough here to actually have common logic here?
        raise NotImplementedError

    def short_summary(self):
        """
        A short-line text-only summary of the event for summary displays
        """
        raise NotImplementedError

    def to_html(self):
        """
        A detailed HTML presentation of this event
        """
        raise NotImplementedError
