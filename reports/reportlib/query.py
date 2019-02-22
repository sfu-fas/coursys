import time 
import copy
import json
import datetime
import iso8601
import pytz
import os
import string

from .table import Table

from django.conf import settings

no_function = lambda x: x

class DefaultLog(object):
    def __init__(self):
        pass
    def log(self, x):
        pass
        #print x

class BaseQuery(object):
    """ The base class for queries. Performs a simple DB query. """

    query = string.Template(
        """
        SELECT emplid FROM ps_stdnt_car_term
        FETCH FIRST 10 ROWS ONLY
        """)
    default_arguments = { } 
    filename="query"
    logger = DefaultLog()

    @classmethod
    def set_logger(cls, logger):
        BaseQuery.logger = logger

    def __init__(self, db, input_clean_function=no_function, output_clean_function=no_function, query_args={}):
        """ 
            db - a PEP-249 compliant DB connection.
            input_clean_function - a function to convert arguments into 
                                    database-friendly strings
            output_clean_function - a function to sanitize db output
            query_args - an object containing the query's arguments
        """
        self.db_connection = db
        # merge the query_args against the argument_defaults
        temp_args = copy.deepcopy(self.default_arguments)
        temp_args.update( query_args ) 
        self.arguments = temp_args
        
        # any arguments passed, run through the clean function
        for arg in self.arguments:
            self.arguments[arg] = input_clean_function(self.arguments[arg])
        self.output_clean_function = output_clean_function


    @property
    def complete_query(self):
        return self.query.substitute( self.arguments)

    def result(self):
        """ Perform the query, and return the result as a Table object """

        BaseQuery.logger.log( "With arguments: " + str(self.arguments) )
        BaseQuery.logger.log( "Running query: \n" + str(self.complete_query) )

        cursor = self.db_connection.cursor()

        start_time = time.time()
        cursor.execute( self.complete_query ) 
        self.elapsed_time = time.time() - start_time

        BaseQuery.logger.log( str(self.elapsed_time) + " seconds" )

        results_table = Table()
        
        for col in cursor.description:
            results_table.append_column( col[0] )

        row = cursor.fetchone()
        while row:
            results_table.append_row( [self.output_clean_function(i) for i in row] )
            row = cursor.fetchone()

        self.rows_fetched = len(results_table) 

        BaseQuery.logger.log( str(self.rows_fetched) + " rows fetched" )

        return results_table

    def __hash__(self):
        return hash(self.complete_query )

def force_dir( path ):
    """ Forces an empty directory to exist at path (if possible.) """
    if not os.path.exists(path):
        os.makedirs(path)
    return path

class CachedQuery(BaseQuery):
    """ Decorates the base query with a file caching layer.
    
        Children of CachedQuery can modify how long the query is cached for 
        by altering the 'expires' variable. The default is '1 day'. 
    """ 

    expires = datetime.datetime.now() + datetime.timedelta(1) 

    @staticmethod
    def cache_location():
        if not os.path.exists(settings.REPORT_CACHE_LOCATION):
            os.makedirs(settings.REPORT_CACHE_LOCATION)
        return settings.REPORT_CACHE_LOCATION
    
    @property
    def query_filename(self):
        force_dir(CachedQuery.cache_location())
        return os.path.join(CachedQuery.cache_location(),  self.filename + str(hash(self)) + ".query")
    @property
    def result_filename(self):
        force_dir(CachedQuery.cache_location())
        return os.path.join(CachedQuery.cache_location(), self.filename + str(hash(self)) + ".result")

    def is_cached_on_file(self):
        if os.path.exists( self.query_filename ):
            with open(self.query_filename, 'r') as f:
                obj = json.loads( f.read() ) 
                expires = iso8601.parse_date(obj['expires'])
                if pytz.UTC.localize(datetime.datetime.now()) < expires:
                    return True
                BaseQuery.logger.log("Cache expired.")
        return False
    
    def serialize_query(self):
        obj = {}
        obj['query'] = self.query.template
        obj['args'] = self.arguments
        obj['expires'] = pytz.UTC.localize(self.expires).isoformat()
        obj['elapsed_time'] = self.elapsed_time
        obj['rows_fetched'] = self.rows_fetched
        return json.dumps(obj, indent=4) 

    def load_query(self):
        with open(self.query_filename, 'r') as f:
            obj = json.loads( f.read() ) 
            self.elapsed_time = obj['elapsed_time']
            self.rows_fetched = obj['rows_fetched']

    def save_query(self):
        with open(self.query_filename, 'w') as f:
            f.write( self.serialize_query() )

    def save_result(self):
        self.cached_result.to_csv(self.result_filename)

    def load_result(self):
        self.cached_result = Table.from_csv(self.result_filename)

    def return_cached_result(self):
        return copy.deepcopy( self.cached_result )
    
    def result(self):
        """ Wraps the 'result' function in caching code."""
        if hasattr(self, 'cached_result'):
            CachedQuery.logger.log( " -- Loading from cache -- " )
            return self.return_cached_result()
        if self.is_cached_on_file():
            CachedQuery.logger.log( "With arguments: " + str(self.arguments) )
            CachedQuery.logger.log( " -- Loading from file: " + str(self.query_filename) + " --" )
            self.load_query()
            self.load_result()
            return self.return_cached_result()
        else:
            self.cached_result = super(CachedQuery, self).result()
            self.save_query()
            self.save_result()
            return self.return_cached_result()
    
    @staticmethod
    def clear_expired_members_from_cache():
        """ Remove any files from the cache if they've expired. """

        cache_location = CachedQuery.cache_location() 
        CachedQuery.logger.log( "Looking for expired cache members in " + cache_location )
        if not os.path.isdir(cache_location):
            CachedQuery.logger.log( "Cache directory not found.")
            return
        for cache_file in os.listdir(cache_location):
            cache_file = os.path.join(cache_location, cache_file )
            if cache_file.endswith('.query') and os.path.isfile( cache_file ):
                with open(cache_file, 'r') as f:
                    obj = json.loads( f.read() ) 
                    expires = iso8601.parse_date(obj['expires'])
                    if not pytz.UTC.localize(datetime.datetime.now()) < expires:
                        result_file = cache_file.replace('.query', '.result')
                        os.remove( cache_file ) 
                        os.remove( result_file )
                        CachedQuery.logger.log( "Deleting expired cache: " + cache_file + ", " + result_file )

class Query(CachedQuery):
    pass



class LocalDBQuery(Query):
    """
    Query on the local Django database.

    Must override query_values which should be a list of dicts: SomeModel.objects.all().values() or similar.

    May override field_map to rename resulting columns, and post_process() to mangle the resulting Table.
    """
    field_map = {}

    def __init__(self, *args, **kwargs):
        super(LocalDBQuery, self).__init__(db=None, *args, **kwargs)

    def post_process(self):
        pass

    def result(self):
        results_table = Table()
        qs = list(self.query_values)

        cols = list(qs[0].keys())
        for k in cols:
            results_table.append_column(self.field_map.get(k, k))

        for row in qs:
            results_table.append_row( [self.output_clean_function(row[c]) for c in cols] )

        self.results_table = results_table
        self.post_process()

        return self.results_table
