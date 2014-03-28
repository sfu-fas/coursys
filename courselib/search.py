import re

from django.db.models import Q

def find_userid_or_emplid(userid):
    """
    Search by userid or emplid
    """
    try:
        int(userid)
        return Q(userid=userid) | Q(emplid=userid)
    except ValueError:
        return Q(userid=userid)

# adapted from http://julienphalip.com/post/2825034077/adding-search-to-a-django-site-in-a-snap

def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:
        
        >>> normalize_query('  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
    
    '''
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)] 

def get_query(query_string, search_fields, startonly=False):
    ''' Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.
    
    startonly=True searches only at start of field/word.
    '''
    query = Q() # Query to search for every search term
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            if startonly:
                q = Q(**{"%s__istartswith" % field_name: term}) \
                    | Q(**{"%s__icontains" % field_name: ' '+term}) 
            else:
                q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query


from django.db import models
from haystack.signals import RealtimeSignalProcessor

from pages.models import Page, PageVersion

class SelectiveRealtimeSignalProcessor(RealtimeSignalProcessor):
    """
    Allows for observing when saves/deletes fire & automatically updates the
    search engine appropriately.
    """
    def handle_save(self, sender, instance, **kwargs):
        if sender == Page:
            # reindex Page
            return super(SelectiveRealtimeSignalProcessor, self).handle_save(sender=sender, instance=instance, **kwargs)
        elif sender == PageVersion:
            # reindex corresponding Page
            page = instance.page
            self.handle_save(Page, page)

    def handle_delete(self, sender, instance, **kwargs):
        # Page and PageVersion don't get deleted
        pass