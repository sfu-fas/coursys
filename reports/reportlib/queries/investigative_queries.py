from ..db2_query import DB2_Query, Unescaped
import string
import datetime

class OneRowTableQuery(DB2_Query):
    title="One Row Query"
    description="Retrieve one row from a table." 
    expires = datetime.datetime.now() + datetime.timedelta(100) 
    query = string.Template("""
    SELECT
        *
    FROM 
        $table
    FETCH FIRST 1 ROWS ONLY
        """)
    
    def __init__(self, query_args):
        query_args['table'] = Unescaped(query_args['table'])
        self.title = "One Row Query - " + query_args["table"]
        super(OneRowTableQuery, self).__init__(query_args)

class TableSizeQuery(DB2_Query):
    title="Table Size Query"
    description="Return number of rows in a table."
    expires = datetime.datetime.now() + datetime.timedelta(100) 
    query = string.Template("""
    SELECT 
        COUNT(*)
    FROM
        $table
    """)
    def __init__(self, query_args):
        query_args['table'] = Unescaped(query_args['table'])
        self.title = "Table Size Query - " + query_args["table"]
        super(TableSizeQuery, self).__init__(query_args)


class DistinctFromColumnQuery(DB2_Query):
    title="Distinct From Column Query" 
    description="Select all of the distinct options from a column in a table."
    expires = datetime.datetime.now() + datetime.timedelta(100) 
    query = string.Template("""
    SELECT DISTINCT
        $column
    FROM 
        $table
    """)
    def __init__(self, query_args):
        query_args['table'] = Unescaped(query_args['table'])
        query_args['column'] = Unescaped(query_args['column'])
        self.title = "Distinct From Column Query - " + query_args['table'] + "." + query_args['column'] 
        super(DistinctFromColumnQuery, self).__init__(query_args)

