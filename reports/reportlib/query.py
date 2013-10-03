import time 
import copy
import json
import datetime
import iso8601
import pytz
import os
import shutil
import string

from table import Table
from title_and_description import TitleAndDescription

no_function = lambda x: x

class __BaseQuery(TitleAndDescription):
    """ The base class for queries. Performs a simple DB query. """

    title = "Base Query"
    description = "This is a plain-text description of what the query does."
    query = string.Template(
        """
        SELECT emplid FROM ps_stdnt_car_term
        FETCH FIRST 10 ROWS ONLY
        """)
    default_arguments = { } 

    def __init__(self, db, input_clean_function=no_function, output_clean_function=no_function, query_args={}, verbose=True):
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

        self.verbose = verbose

    @property
    def complete_query(self):
        return self.query.substitute( self.arguments)

    def result(self):
        """ Perform the query, and return the result as a Table object """

        if self.verbose:
            print "With arguments: ", self.arguments
            print "Running query: \n", self.complete_query

        cursor = self.db_connection.cursor()

        start_time = time.time()
        cursor.execute( self.complete_query ) 
        self.elapsed_time = time.time() - start_time

        if self.verbose:
            print self.elapsed_time, "seconds"

        results_table = Table()
        results_table.title = self.title + " Result" 
        results_table.description = self.description 
        
        for col in cursor.description:
            results_table.append_column( col[0] )

        row = cursor.fetchone()
        while row:
            results_table.append_row( [self.output_clean_function(i) for i in row] )
            row = cursor.fetchone()

        self.rows_fetched = len(results_table) 

        if self.verbose:
            print self.rows_fetched, "rows fetched"

        return results_table

    def __hash__(self):
        return hash(self.complete_query )

class CachedQuery(__BaseQuery):
    """ Decorates the base query with a file caching layer.
    
        Children of CachedQuery can modify how long the query is cached for 
        by altering the 'expires' variable. The default is '1 day'. 
    """ 

    expires = datetime.datetime.now() + datetime.timedelta(1) 
    
    @property
    def query_filename(self):
        return os.path.join( "cache",  self.filename + str(hash(self)) + ".query")
    @property
    def result_filename(self):
        return os.path.join( "cache", self.filename + str(hash(self)) + ".result")

    def is_cached_on_file(self):
        if os.path.exists( self.query_filename ):
            with open(self.query_filename, 'r') as f:
                obj = json.loads( f.read() ) 
                expires = iso8601.parse_date(obj['expires'])
                if pytz.UTC.localize(datetime.datetime.now()) < expires:
                    return True
                elif self.verbose:
                    print "Cache expired."
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
        self.cached_result = Table.from_csv(self.result_filename, self.title + " Result", self.description)

    def return_cached_result(self):
        return copy.deepcopy( self.cached_result )
    
    def result(self):
        """ Wraps the 'result' function in caching code."""
        if hasattr(self, 'cached_result'):
            if self.verbose:
                print " -- Loading from cache -- "
            return self.return_cached_result()
        if self.is_cached_on_file():
            if self.verbose:
                print "With arguments: ", self.arguments
                print " -- Loading from file: "+self.query_filename+"  -- "
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
        print "Looking for expired cache members..."
        for cache_file in os.listdir( "cache" ):
            cache_file = os.path.join( "cache", cache_file )
            if cache_file.endswith('.query') and os.path.isfile( cache_file ):
                with open(cache_file, 'r') as f:
                    obj = json.loads( f.read() ) 
                    expires = iso8601.parse_date(obj['expires'])
                    if not pytz.UTC.localize(datetime.datetime.now()) < expires:
                        result_file = cache_file.replace('.query', '.result')
                        os.remove( cache_file ) 
                        os.remove( result_file )
                        print "Deleting expired cache: " + cache_file + ", " + result_file

class Query(CachedQuery):
    pass

