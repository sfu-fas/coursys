from haystack.signals import RealtimeSignalProcessor
from haystack.exceptions import NotHandled
from haystack.query import SearchQuerySet
from django.apps import apps
get_model = apps.get_model

import logging
logger = logging.getLogger(__name__)


class DISABLED_SelectiveRealtimeSignalProcessor(RealtimeSignalProcessor):
    """
    Index changes in real time, but in the specific way we need them updated.
    """
    def handle_save(self, sender, instance, **kwargs):
        cls = sender.__name__

        if cls == 'Page':
            # reindex object in the standard way
            #logger.debug('Reindexing Page %s' % (instance))
            super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)

        elif cls == 'PageVersion':
            # reindex corresponding Page
            #logger.debug('Reindexing PageVersion %s' % (instance))
            Page = get_model('pages', 'Page')
            page = instance.page
            self.handle_save(sender=Page, instance=page)

        elif cls == 'DiscussionTopic':
            #logger.debug('Reindexing DiscussionTopic %s' % (instance))
            if instance.status == 'HID':
                # hidden is deletion
                self.handle_delete(sender=sender, instance=instance, **kwargs)
            else:
                super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)

        elif cls == 'DiscussionMessage':
            # reindex the containing topic
            #logger.debug('Reindexing DiscussionMessage %s' % (instance))
            DiscussionTopic = get_model('discuss', 'DiscussionTopic')
            self.handle_save(sender=DiscussionTopic, instance=instance.topic, **kwargs)

        elif cls == 'CourseOffering':
            #logger.debug('Reindexing CourseOffering %s' % (instance))
            if instance.component == 'CAN':
                # cancelling is our version of deleting
                self.handle_delete(sender=sender, instance=instance)
            else:
                # reindex object in the standard way
                super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)

        elif cls == 'Member':
            #logger.debug('Reindexing Member %s' % (instance))
            if instance.role == 'DROP':
                # dropping is our version of deleting
                self.handle_delete(sender=sender, instance=instance)
            elif instance.role in ['STUD', 'TA']:
                # only students and TAs get indexed as Members
                super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)
            elif instance.role == 'INST':
                # instructor names are part of the CourseOffering index
                CourseOffering = get_model('coredata', 'CourseOffering')
                self.handle_save(sender=CourseOffering, instance=instance.offering, **kwargs)

        elif cls == 'Person':
            #logger.debug('Reindexing Person %s' % (instance))
            # reindex the person themself
            super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)
            # ... and reindex this person as a member of the courses they're in
            Member = get_model('coredata', 'Member')
            members = Member.objects.filter(person=instance, role__in=['STUD', 'INST'])
            for m in members:
                self.handle_save(sender=Member, instance=m, **kwargs)

        elif cls == 'RAAppointment':
            #logger.debug('Reindexing RAAppointment %s' % (instance))
            if instance.deleted:
                # deleted contract
                self.handle_delete(sender=sender, instance=instance, **kwargs)
            else:
                super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)
        
        elif cls == 'RARequest':
            #logger.debug('Reindexing RARequest %s' % (instance))
            if instance.deleted:
                # deleted request
                self.handle_delete(sender=sender, instance=instance, **kwargs)
            else:
                super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)

        elif cls == 'Visa':
            #logger.debug('Reindexing Visa %s' % (instance))
            if instance.deleted:
                # deleted request
                self.handle_delete(sender=sender, instance=instance, **kwargs)
            else:
                super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)

        elif cls == 'GradStudent':
            #logger.debug('Reindexing GradStudent %s' % (instance))
            if instance.deleted:
                # deleted request
                self.handle_delete(sender=sender, instance=instance, **kwargs)
            else:
                super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)
        #else:
        #    ignore everything else, since we don't care.

    def handle_delete(self, sender, instance, **kwargs):
        # modified from BaseSignalProcessor.handle_delete to force checking existence before removing from the index
        # (and getting an error message if it's not there).
        using_backends = self.connection_router.for_write(instance=instance)

        for using in using_backends:
            try:
                index = self.connections[using].get_unified_index().get_index(sender)

                # check to see if the object is actually in the index before removing:
                index.prepare(instance)
                ct = index.prepared_data['django_ct']
                obj_id = index.prepared_data['id']
                existing = SearchQuerySet().models(sender).filter(django_ct=ct, id=obj_id)

                if existing.count() > 0:
                    index.remove_object(instance, using=using)
            except NotHandled:
                pass