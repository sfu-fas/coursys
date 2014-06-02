from haystack.backends.elasticsearch_backend import ElasticsearchSearchEngine, ElasticsearchSearchBackend

class CustomElasticsearchBackend(ElasticsearchSearchBackend):
    """
    The default ElasticsearchSearchBackend settings don't tokenize strings of digits the same way as words, so emplids
    get lost: the lowercase tokenizer is the culprit. Switching to the standard tokenizer and doing the case-
    insensitivity in the filter seems to do the job.
    """
    def __init__(self, connection_alias, **connection_options):
        # see http://stackoverflow.com/questions/13636419/elasticsearch-edgengrams-and-numbers
        self.DEFAULT_SETTINGS['settings']['analysis']['analyzer']['edgengram_analyzer']['tokenizer'] = 'standard'
        self.DEFAULT_SETTINGS['settings']['analysis']['analyzer']['edgengram_analyzer']['filter'].append('lowercase')
        super(CustomElasticsearchBackend, self).__init__(connection_alias, **connection_options)


class CustomElasticsearchSearchEngine(ElasticsearchSearchEngine):
    backend = CustomElasticsearchBackend
