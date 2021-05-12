from haystack.backends.elasticsearch5_backend import Elasticsearch5SearchBackend, Elasticsearch5SearchEngine


class CustomElasticsearchBackend(Elasticsearch5SearchBackend):
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


class CustomElasticsearchSearchEngine(Elasticsearch5SearchEngine):
    backend = CustomElasticsearchBackend
