class SIMSConn(object):
    """
    Singleton object representing SIMS DB connection
    
    singleton pattern implementation from: http://stackoverflow.com/questions/42558/python-and-the-singleton-pattern
    
    Absolutely NOT thread safe.
    Implemented as a singleton to minimize number of times SIMS connection overhead occurs.
    Should only be created on-demand (in function) to minimize startup for non-SIMS requests.
    """
    sims_user = "ggbaker"
    sims_db = "csrpt"
    dbpass_file = "./dbpass"
    
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SIMSConn, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.conn, self.db = self.get_connection()

    def get_connection(self):
        passfile = open(self.dbpass_file)
        _ = passfile.next()
        _ = passfile.next()
        _ = passfile.next()
        simspasswd = passfile.next().strip()
        
        import DB2
        dbconn = DB2.connect(dsn=self.sims_db, uid=self.sims_user, pwd=simspasswd)
        return dbconn, dbconn.cursor()

    def escape_arg(self, a):
        """
        Escape argument for DB2
        """
        # Based on description of PHP's db2_escape_string
        if type(a) in (int,long):
            return str(a)
        
        a = unicode(a).encode('utf8')
        # assume it's a string if we don't know any better
        a = a.replace("\\", "\\\\")
        a = a.replace("'", "\\'")
        a = a.replace('"', '\\"')
        a = a.replace("\r", "\\r")
        a = a.replace("\n", "\\n")
        a = a.replace("\x00", "\\\x00")
        a = a.replace("\x1a", "\\\x1a")
        return "'"+a+"'"

    def execute(self, query, args):
        # should be ensuring real/active connection here?
        clean_args = tuple((self.escape_arg(a) for a in args))
        real_query = query % clean_args
        #print ">>>", real_query
        return self.db.execute(real_query)


    def prep_value(self, v):
        """
        get DB2 value into a useful format
        """
        if isinstance(v, basestring):
            return v.strip().decode('utf8')
        else:
            return v

    def __iter__(self):
        row = self.db.fetchone()
        while row:
            yield tuple((self.prep_value(v) for v in row))
            row = self.db.fetchone()

    def rows(self):
        return list(self.__iter__())


def find_person(emplid):
    """
    Find the person in SIMS: return data or None
    """
    db = SIMSConn()
    db.execute("SELECT emplid, last_name, first_name, middle_name FROM dbsastg.ps_personal_data WHERE emplid=%s",
               (str(emplid),))

    for emplid, last_name, first_name, middle_name in db:
        return {'emplid': emplid, 'last_name': last_name, 'first_name': first_name, 'middle_name': middle_name}


