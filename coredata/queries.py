import DB2
from courselib.search import normalize_query
from coredata.importer_rodb import execute_query, iter_rows, escape_arg

class SIMSConn(object):
    """
    Singleton object representing SIMS DB connection
    
    singleton pattern implementation from: http://stackoverflow.com/questions/42558/python-and-the-singleton-pattern
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
        
        dbconn = DB2.connect(dsn=self.sims_db, uid=self.sims_user, pwd=simspasswd)
        return dbconn, dbconn.cursor()
    
    def execute(self, query, args):
        # should be ensuring real/active connection here?
        execute_query(self.db, query, args)
    def __iter__(self):
        return iter_rows(self.db)
    def iter_rows(self):
        return iter_rows(self.db)
    def rows(self):
        return list(self.iter_rows())


def find_person(emplid):
    """
    Find the person in SIMS: return data or None
    """
    db = SIMSConn()
    db.execute("SELECT emplid, last_name, first_name, middle_name FROM dbsastg.ps_personal_data WHERE emplid=%s fetch first 10 rows only",
               (str(emplid),))

    for emplid, last_name, first_name, middle_name in db:
        return {'emplid': emplid, 'last_name': last_name, 'first_name': first_name, 'middle_name': middle_name}


