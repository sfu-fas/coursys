import collections

class Choices(collections.OrderedDict):
    '''
    An ordered dictionary that also acts as an iterable of (key, value) pairs.
    '''

    def __init__(self, *choices):
        super(Choices, self).__init__(choices)

    def __iter__(self):
        # XXX: Can't call super(Choices, self).iteritems() here because it will call our
        #      __iter__ and recurse infinitely.
        for key in super(Choices, self).__iter__():
            yield (key, self[key])
