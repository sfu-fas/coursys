import pprint 
import csv

class Table():
    EMPTY = "" 

    def __init__(self):
        self.headers = []
        self.rows = []
        self.indices = {}

    def append_column(self, column_name, column_fill=None):
        """ Add an empty column with name 'column_name' to the table

        >>> t = Table()
        >>> t.append_column("Person")
        >>> t.append_column("Place")
        >>> print t
        Person | Place
        """
        if column_fill == None:
            column_fill = Table.EMPTY

        self.headers.append( column_name )
        for row in self.rows:
            row.append( column_fill )
    
    def append_row(self, row):
        """ Add a new row to the table.

        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> print t
        FirstName | LastName
        Curtis | Lassam
        """
        self.rows.append( row ) 

    @property
    def is_very_large(self):
        return len(self.rows) > 100000;

    def compute_column( self, column_name, column_function):
        """ Compute a new column, row by row, using the function provided. 
        
        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> full_name_fn = lambda x: x["FirstName"] + " " + x["LastName"] 

        >>> t.compute_column( "FullName", full_name_fn )
        >>> print t 
        FirstName | LastName | FullName
        Curtis | Lassam | Curtis Lassam
        Jonathan | Lassam | Jonathan Lassam
       
        """
        if column_name in self.headers:
            self.remove_column(column_name)

        for i in range( 0, len(self.rows) ):
            self.rows[i].append( column_function( self.row_map(i) ) )

        self.headers.append( column_name )

    def remove_column( self, column_name ):
        """ Remove a column from the table

        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> t.remove_column("FirstName")
        >>> print t 
        LastName
        Lassam
        Lassam
        
        """
        index_to_remove = self.headers.index(column_name)
        del self.headers[index_to_remove]
        for row in self.rows:
            del row[index_to_remove]

    def column_as_list( self, column_name ):
        """ Retrieve a column from the table as a list.

        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> print t.column_as_list("FirstName")
        ['Curtis', 'Jonathan']

        """
        index = self.headers.index(column_name)
        return [ row[index] for row in self.rows ]

    def subset( self, list_of_columns ):
        """ Produce a new table, containing only the listed columns. """

        t = Table()
        for row_map in self.row_maps():
            new_row = []
            for column in list_of_columns:
                new_row.append( row_map[column] ) 
            t.append_row( new_row )
        for column in list_of_columns:
            t.headers.append(column) 

        return t
            
    def row_map( self, i ):
        """ For the i-th row in the table, return a column-name to data map 
        
        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        
        >>> t.row_map( 0 )
        {'LastName': 'Lassam', 'FirstName': 'Curtis'}

        >>> t.row_map( 1 )
        {'LastName': 'Lassam', 'FirstName': 'Jonathan'}

        """
        row = self.rows[i]
        obj = {}
        for i in range( 0, len(self.headers) ):
            obj[self.headers[i]] = row[i]
        return obj

    def row_maps( self ):
        """ Iterate through the table, returning a row_map for every row. 

        This function returns an iterator, not a list.
        To create a list from row_maps, use list(self.row_maps()).

        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        
        >>> [ x for x in t.row_maps() ]
        [{'LastName': 'Lassam', 'FirstName': 'Curtis'}, {'LastName': 'Lassam', 'FirstName': 'Jonathan'}]

        """
        for i in range( 0, len(self.rows) ):
            yield self.row_map(i) 

    def filter( self, filter_function ):
        """ Remove any row objects that do not match the filter function. 

        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> filter_fn = lambda x: x["FirstName"] != "Curtis" 

        >>> t.filter( filter_fn )
        FirstName | LastName
        Jonathan | Lassam

        Because this performs a complete pass through the table, it is 
        more efficient to chain filters together, like this: 

        >>> not_curtis = lambda x: x["FirstName"] != "Curtis" 
        >>> not_lassam = lambda x: x["LastName"] != "Lassam"
        >>> not_curtis_or_lassam = lambda x: not_curtis(x) and not_lassam(x)
        >>> t.append_row( ["Peter", "Ox-Hands"] )
        >>> t.filter( not_curtis_or_lassam )
        FirstName | LastName
        Peter | Ox-Hands

        """
        for i in range( len(self.rows)-1, -1, -1 ):
            if not filter_function( self.row_map(i) ):
                del self.rows[i]
        return self

    def find( self, key_column, value ):
        """ Search for the first matching object in the table.
        
        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> t.find( "FirstName", "Curtis" )
        0
        >>> t.find( "FirstName", "Jonathan")
        1
        >>> t.find( "FirstName", "Jonas")
        -1
        
        """
        
        # Indexed search.  O(1)
        if key_column in self.indices:
            try:
                return self.indices[key_column][value]
            except KeyError:
                return -1
        
        # Linear search. O(n)
        for i in range( 0, len(self.rows) ):
            if self.row_map(i)[key_column] == value:
                return i
        return -1

    def contains( self, key_column, value):
        """ Return True if the table contains 'value' in 'column', false otherwise. 
        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> t.contains( "FirstName", "Curtis" )
        True
        >>> t.contains( "LastName", "Hormel" )
        False
        """
        if self.find( key_column, value ) == -1:
            return False
        else:
            return True

    def generate_index( self, key_column ):
        """ Creates an index on the column in question to speed up 'find'

        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> t.generate_index( "FirstName") 

        These find operations now occur in O(1) instead of O(n) 
        >>> t.find( "FirstName", "Curtis" )
        0
        >>> t.find( "FirstName", "Jonathan")
        1
        >>> t.find( "FirstName", "Randall")
        -1

        Note that, for now, the index is not modified when a new row is added.
        That's a definite TODO.

        >>> t.append_row( ["Randall", "Mouthharp"] )
        >>> t.find( "FirstName", "Randall" )
        -1

        >>> t.generate_index( "FirstName" )
        >>> t.find( "FirstName", "Randall" )
        2

        It's also important to note that the find operation still must always
        return the _first_ match in the list.
        >>> t.append_row( ["Curtis", "Incorrect"] )
        >>> t.generate_index( "FirstName" )
        >>> t.find( "FirstName", "Curtis" )
        0

        """
        self.indices[key_column] = {}
        for i in range( 0, len(self.rows) ):
            row_map = self.row_map(i) 
            key = self.row_map(i)[key_column]
            if key not in self.indices[key_column]:
                self.indices[key_column][key] = i

    def compute_key( self, key_name, column_names ):
        """ Creates an indexed key out of multiple tables.

        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> t.compute_key( "FullName", ["FirstName", "LastName"]) 
        >>> print t
        FirstName | LastName | FullName
        Curtis | Lassam | Curtis-Lassam
        Jonathan | Lassam | Jonathan-Lassam

        generate_index is called on the created key

        >>> t.find( "FullName", "Curtis-Lassam" )
        0
        """

        def concatenate( row_map ):
            return "-".join( [row_map[column] for column in column_names] )
        self.compute_column( key_name, concatenate ) 
        self.generate_index( key_name )

    def inner_join( self, other_table, key_column ):
        """ Inner joins 'other_table' to this table on key_column.

        >>> t1 = Table()
        >>> t1.append_column("Id")
        >>> t1.append_column("LastName")
        >>> t1.append_row( [ 11, "Lassam"] )
        >>> t1.append_row( [ 12, "Goofus"] )
        >>> t1.append_row( [ 13, "Gallant"] )

        >>> t2 = Table()
        >>> t2.append_column("Id")
        >>> t2.append_column("Wage")
        >>> t2.append_row( [ 12, "$150,000"] )
        >>> t2.append_row( [ 11, "Not telling"] )
        >>> t2.append_row( [ 14, "$12,000"] )

        >>> t1.inner_join( t2, "Id" )
        >>> print t1
        Id | LastName | Wage
        11 | Lassam | Not telling
        12 | Goofus | $150,000

        """
        self.generate_index(key_column)
        other_table.generate_index(key_column) 

        for i in range( len(self.rows)-1, -1, -1 ): 
            key = self.row_map(i)[key_column]
            loc = other_table.find(key_column, key)
            if loc == -1:
                del self.rows[i]
            else:
                other_row = other_table.rows[loc]
                self.rows[i].extend(other_row)
        for header in other_table.headers:
            if header in self.headers:
                header = header + "_JOIN"
            self.headers.append( header )

        self.remove_column( key_column + "_JOIN" )
    
    def left_join( self, other_table, key_column ):
        """ left joins 'other_table' to this table on key_column, 
            but just disregards nonexistent columns 

        >>> t1 = Table()
        >>> t1.append_column("Id")
        >>> t1.append_column("LastName")
        >>> t1.append_row( [ 11, "Lassam"] )
        >>> t1.append_row( [ 12, "Goofus"] )
        >>> t1.append_row( [ 13, "Gallant"] )

        >>> t2 = Table()
        >>> t2.append_column("Id")
        >>> t2.append_column("Wage")
        >>> t2.append_row( [ 12, "$150,000"] )
        >>> t2.append_row( [ 11, "Not telling"] )
        >>> t2.append_row( [ 14, "$12,000"] )

        >>> t1.left_join( t2, "Id" )
        >>> print t1
        Id | LastName | Wage
        11 | Lassam | Not telling
        12 | Goofus | $150,000
        13 | Gallant | 

        """
        self.generate_index(key_column)
        other_table.generate_index(key_column) 

        blank_row = ["" for x in other_table.headers]

        for i in range( len(self.rows)-1, -1, -1 ): 
            key = self.row_map(i)[key_column]
            loc = other_table.find(key_column, key)
            if loc == -1:
                self.rows[i].extend(blank_row)
            else:
                other_row = other_table.rows[loc]
                self.rows[i].extend(other_row)
        for header in other_table.headers:
            if header in self.headers:
                header = header + "_JOIN"
            self.headers.append( header )

        self.remove_column( key_column + "_JOIN" )

    def flatten(self, key_column):
        """ If there are duplicate items in key_column, merge them into a single
        column by concatenating other columns.

        Eliminate duplicates. 
        
        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_column("Thirdthing")
        >>> t.append_row( ["Curtis", "Lassam", "999"] )
        >>> t.append_row( ["Jonathan", "Lassam", "1010"] )
        >>> t.append_row( ["Curtis", "Lassam", "2282"] )
        >>> t.append_row( ["Bippity", "Spoon", "9992"] )
        >>> t.append_row( ["", "Onion", "9129"] )
        >>> t.append_row( ["Jiggity", "Onion", "2123"] )
        >>> t.flatten( "LastName" )
        FirstName | LastName | Thirdthing
        Curtis, Jonathan | Lassam | 999, 1010, 2282
        Bippity | Spoon | 9992
        Jiggity | Onion | 9129, 2123
        
        """ 
        key_index = self.headers.index(key_column)
        assert( key_index != -1) 
        delete_rows = []
        self.generate_index(key_column)
        for i in range( 0, len(self.rows) ):
            key = self.rows[i][key_index]
            first_appearance_of_key = self.find(key_column, key)
            if first_appearance_of_key != i:
                this_row = self.rows[i]
                target_row = self.rows[first_appearance_of_key]
                # merge this row with the first row.
                for j in range( 0, len(self.rows[i])):
                    if this_row[j] == target_row[j]:
                        pass
                    elif this_row[j] == Table.EMPTY:
                        pass
                    elif target_row[j] == Table.EMPTY:
                        target_row[j] = this_row[j]
                    elif this_row[j] + "," in target_row[j] or ", " + this_row[j] in target_row[j]:
                        pass
                    else:
                        target_row[j] = str(target_row[j]) + ", " + str(this_row[j])
                delete_rows.append(i)

        delete_rows.reverse()
        for row_index in delete_rows:
            del self.rows[row_index]
        
        return self

    def to_dict(self):
        """ Returns an object representation of this table. 

        Used for serialization.

        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> t.to_dict()
        {'headers': ['FirstName', 'LastName'], 'rows': [['Curtis', 'Lassam'], ['Jonathan', 'Lassam']]}

        """

        obj = {}
        obj['headers'] = self.headers
        obj['rows'] = self.rows
        return obj
    
    @staticmethod
    def from_dict(obj):
        """ Creates a table from an object representation. 

        Used for deserialization.

        >>> obj = {'headers': ['FirstName', 'LastName'], 'rows': [['Curtis', 'Lassam'], ['Jonathan', 'Lassam']]}

        >>> print Table.from_dict( obj ) 
        FirstName | LastName
        Curtis | Lassam
        Jonathan | Lassam
        
        """
        table = Table()
        for header in obj['headers']:
            table.append_column( header )
        for row in obj['rows']:
            table.append_row( row )
        return table

    def __repr__(self):
        """ Return a string representation of the data. 

            Changing __repr__ will break most of the doctests, here. 
            If you need a pretty-printed table, use self.pretty_print() instead.
        """
        list_of_strings = []
        list_of_strings.append( " | ".join( self.headers ) )
        for row in self.rows:
            list_of_strings.append( " | ".join( [Table.asciify(x) for x in row] ))

        return "\n".join(list_of_strings)

    @staticmethod
    def asciify(thing):
        if type(thing) is str:
            return thing.encode('ascii', 'ignore')
        if type(thing) is not str:
            return str(thing)
        else:
            return thing

    @staticmethod
    def utf8(thing):
        if type(thing) is str:
            return thing.encode('utf-8', 'ignore')
        else:
            return thing

    def pretty_print(self):
        """ Return a pretty string representation of the data.

            Currently... not quite implemented. 
        """
        return self.__repr__()

    def pretty_print_objects(self):
        """ Print a flat list of objects in the table.

        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> t.pretty_print_objects()
        {   'FirstName': 'Curtis',
            'LastName': 'Lassam'}
        -------------------
        {   'FirstName': 'Jonathan',
            'LastName': 'Lassam'}
        -------------------

        """
        pretty_print = pprint.PrettyPrinter(indent=4,width=10)
        list_of_strings = []
        for row_map in self.row_maps():
            pretty_print.pprint(row_map)
            print("-------------------")

    def to_csv(self, location):
        """ Print the table to a csv file. 
        
        >>> t = Table()
        >>> t.append_column("FirstName")
        >>> t.append_column("LastName")
        >>> t.append_row( ["Curtis", "Lassam"] )
        >>> t.append_row( ["Jonathan", "Lassam"] )
        >>> t.to_csv("/tmp/example.csv")
        >>> h = Table.from_csv( "/tmp/example.csv")
        >>> print h
        FirstName | LastName
        Curtis | Lassam
        Jonathan | Lassam
        
        """
        writer = csv.writer( open(location, 'wb') )
        writer.writerow( self.headers )
        for row in self.rows:
            writer.writerow( [Table.utf8(x) for x in row] )
    
    @staticmethod
    def from_csv(location):
        """ Load the table from a csv file. """
        #reader = unicode_csv.UnicodeCsvReader( open(location, 'rb') )
        reader = csv.reader( open(location, 'rb') )
        
        new_table = Table()
        
        for row in reader:
            for column in row:
                new_table.append_column( column )
            break

        app = new_table.rows.append
        [ app( row ) for row in reader ]

        return new_table

    def convert_to_unicode(self):
        """ Convert the entire contents of the table to unicode. 

        Reasonably expensive, don't call unless you are about to render the table."""
        self.rows = [[Table.to_unicode(column) for column in row] for row in self.rows  ]
    
    @staticmethod
    def to_unicode(thing):
        if type(thing) is str:
            return thing
        if type(thing) is str:
            return str( thing, 'utf-8' )
        else: 
            return str( thing )
    
    def __len__(self):
        return len(self.rows)


