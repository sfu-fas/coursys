from django.utils.html import mark_safe


class EventBase(object):
    pass


class CommentEventBase(EventBase):
    """
    Base class for events that are mostly a comment box.
    """
    @property
    def form_class(self, event=None):
        return SomeFormClass(initial=event.data_as_dict_or_whatever())

    def as_html(self):
        html = '<div>Event As HTML</div>'
        return mark_safe(html)


class FileEventBase(EventBase):
    """
    Base class for events that are mostly a file upload.
    """
    pass


class EmployerEvent(EventBase):
    name = 'Employer/Job'


class QuoteEvent(CommentEventBase):
    name = 'Quote'


class PhotoEvent(FileEventBase):
    name = 'Photo'