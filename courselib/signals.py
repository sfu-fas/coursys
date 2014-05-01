from haystack.signals import BaseSignalProcessor

from coredata.models import Person, CourseOffering, Member
from pages.models import Page, PageVersion

class SelectiveRealtimeSignalProcessor(BaseSignalProcessor):
    """
    Index changes in real time, but in the specific way we need them updated.
    """
    def handle_save(self, sender, instance, **kwargs):
        if sender == Page:
            # reindex object in the standard way
            super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)

        elif sender == PageVersion:
            # reindex corresponding Page
            page = instance.page
            self.handle_save(sender=Page, instance=page)

        elif sender == CourseOffering:
            if instance.component == 'CAN':
                # cancelling is our version of deleting
                self.handle_delete(sender=sender, instance=instance)
            else:
                # reindex object in the standard way
                super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)

        elif sender == Member:
            if instance.role == 'DROP':
                # dropping is our version of deleting
                self.handle_delete(sender=sender, instance=instance)
            elif instance.role == 'STUD':
                # only students get indexed as Members
                super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)
            elif instance.role == 'INST':
                # instructor names are part of the CourseOffering index
                self.handle_save(sender=CourseOffering, instance=instance.offering, **kwargs)

        elif sender == Person:
            # reindex the person themself
            super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)
            # ... and reindex this person as a member of the courses they're in
            members = Member.objects.filter(person=instance, role__in=['STUD', 'INST'])
            for m in members:
                self.handle_save(sender=Member, instance=m, **kwargs)

        #else:
        #    ignore everything else, since we don't care.

    #def handle_delete(self, sender, instance, **kwargs):
    #    return super(SelectiveRealtimeSignalProcessor, self).handle_delete(sender=sender, instance=instance, **kwargs)
