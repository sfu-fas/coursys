import re
from typing import Type, Iterable

from django.conf import settings
from django.db import models

from django.core.management import call_command
from django.db.models import Q
from haystack.utils import loading


def find_userid_or_emplid(userid):
    """
    Search by userid or emplid
    """
    try:
        int(userid)
        return Q(userid=userid) | Q(emplid=userid)
    except ValueError:
        return Q(userid=userid)

def find_member(userid):
    """
    Search Member (or other thing with a .person) by userid or emplid
    """
    try:
        int(userid)
        return Q(person__userid=userid) | Q(person__emplid=userid)
    except ValueError:
        return Q(person__userid=userid)

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


# aliases to the haystack management commands, for convenience

def haystack_update_index():
    call_command("update_index", verbosity=0, remove=True)


def haystack_rebuild_index():
    call_command("rebuild_index", verbosity=0, interactive=False)


def haystack_clear_index():
    call_command("clear_index", verbosity=0, interactive=False)


def haystack_index(model: Type[models.Model], qs: Iterable[models.Model], commit=True):
    """
    Create/update haystack index of collection of instances of the given `model`.

    i.e. imitate haystack's update_index.Command.handle, but only index `qs`, not some larger queryset

    e.g.
    haystack_index(Foo, Foo.objects.filter(interesting=True))
    """
    haystack_connections = loading.ConnectionHandler(settings.HAYSTACK_CONNECTIONS)
    backends = haystack_connections.connections_info.keys()
    for using in backends:
        backend = haystack_connections[using].get_backend()
        unified_index = haystack_connections[using].get_unified_index()
        index = unified_index.get_index(model)
        backend.update(index, qs, commit=commit)