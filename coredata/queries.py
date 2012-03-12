from coredata.models import Person
from django.db import transaction
from django.core.cache import cache
import re

multiple_breaks = re.compile(r'\n\n+')

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
    table_prefix = "dbsastg."
    
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
        SIMSConn.DatabaseError = DB2.DatabaseError
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
        "Execute a query, safely substituting arguments"
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
        "Iterate query results"
        row = self.db.fetchone()
        while row:
            yield tuple((self.prep_value(v) for v in row))
            row = self.db.fetchone()

    def rows(self):
        "List of query results"
        return list(self.__iter__())


class SIMSProblem(unicode):
    """
    Class used to pass back problems with the SIMS connection.
    """
    pass

def SIMS_problem_handler(func):
    """
    Decorator to deal somewhat gracefully with any SIMS database problems.
    Any decorated function may return a SIMSProblem instance to indicate a
    problem with the database connection.
    
    Should be applied to any functions that use a SIMSConn object.
    """
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # check for the types of errors we know might happen
            # (need more than regular exception syntax, since SIMSConn.DatabaseError isn't always there)
            if hasattr(SIMSConn, 'DatabaseError') and isinstance(e, SIMSConn.DatabaseError):
                return SIMSProblem("could not connect to reporting database")
            elif isinstance(e, ImportError):
                return SIMSProblem("could not import DB2 module")
            raise e

    wrapped.__name__ = func.__name__
    return wrapped

def cache_by_emplid(func, seconds=38800): # 8 hours by default
    """
    Decorator to cache query results from SIMS (if successful: no SIMSProblem).
    Requires an 'emplid' argument to the function that uniquely identifies the results.
    Return results must be pickle-able so they can be cached. 
    """
    def wrapped(emplid, *args, **kwargs):
        key = "simscache-" + func.__name__ + "-" + str(emplid)
        # first check cache
        cacheres = cache.get(key)
        if cacheres:
            return cacheres
        
        # not in cache: calculate
        kwargs['emplid'] = emplid
        res = func(*args, **kwargs)
        if isinstance(res, SIMSProblem):
            # problem: don't cache
            return res
        
        # real result: cache it
        cache.set(key, res, seconds)
        return res
    
    wrapped.__name__ = func.__name__
    return wrapped

@cache_by_emplid
@SIMS_problem_handler
def find_person(emplid):
    """
    Find the person in SIMS: return data or None (not found) or a SIMSProblem instance (error message).
    """
    db = SIMSConn()
    db.execute("SELECT emplid, last_name, first_name, middle_name FROM " + db.table_prefix + "ps_personal_data WHERE emplid=%s",
               (str(emplid),))

    for emplid, last_name, first_name, middle_name in db:
        # use emails to guess userid: if not found, leave unset and hope AMAINT has it on next nightly update
        userid = None
        db.execute("SELECT e_addr_type, email_addr, pref_email_flag FROM " + db.table_prefix + "ps_email_addresses c WHERE emplid=%s", (str(emplid),))
        for _, email_addr, _ in db:
            if email_addr.endswith('@sfu.ca'):
                userid = email_addr[:-7]

        return {'emplid': emplid, 'last_name': last_name, 'first_name': first_name, 'middle_name': middle_name, 'userid': userid}

def add_person(emplid):
    """
    Add a Person object based on the found SIMS data
    """
    data = find_person(emplid)
    if not data:
        return
    elif isinstance(data, SIMSProblem):
        return data

    with transaction.commit_on_success():
        ps = Person.objects.filter(emplid=data['emplid'])
        if ps:
            # person already there: ignore
            return ps[0]
        p = Person(emplid=data['emplid'], last_name=data['last_name'], first_name=data['first_name'],
                   pref_first_name=data['first_name'], middle_name=data['middle_name'], userid=data['userid'])
        p.save()
    return p


@cache_by_emplid
@SIMS_problem_handler
def more_personal_info(emplid):
    """
    Get contact info for student: return data or None (not found) or a SIMSProblem instance (error message).
    
    Returns the same dictionary format as Person.config (for the fields it finds).
    """
    # TODO: importer_rodb should use this.
    db = SIMSConn()
    data = {}
    
    # get phone numbers
    db.execute('SELECT phone_type, country_code, phone, extension, pref_phone_flag FROM ' + db.table_prefix + 'ps_personal_phone WHERE emplid=%s', (str(emplid),))
    phones = {}
    data['phones'] = phones
    for phone_type, country_code, phone, extension, pref_phone in db:
        full_number = phone.replace('/', '-')
        if country_code:
            full_number = country_code + '-' + full_number
        if extension:
            full_number = full_number + " ext " + extension
        
        if pref_phone == 'Y':
            phones['pref'] = full_number
        if phone_type == 'HOME':
            phones['home'] = full_number
        elif phone_type == 'CELL':
            phones['cell'] = full_number
        elif phone_type == 'MAIN':
            phones['main'] = full_number
    
    # get addresses
    # sorting by effdt to get the latest in the dictionary
    db.execute("SELECT address_type, effdt, eff_status, c.descrshort, address1, address2, address3, address4, city, state, postal FROM " + db.table_prefix + "ps_addresses a, " + db.table_prefix + "ps_country_tbl c WHERE emplid=%s AND eff_status='A' AND a.country=c.country ORDER BY effdt ASC", (str(emplid),))
    addresses = {}
    data['addresses'] = addresses
    for address_type, _, _, country, address1, address2, address3, address4, city, state, postal in db:
        cityline = city
        if state:
            cityline += ', ' + state
        if country != 'Canada':
            cityline += ', ' + country
        full_address = '\n'.join((address1, address2, address3, address4, cityline, postal))
        full_address = multiple_breaks.sub('\n', full_address)
        
        if address_type == 'HOME':
            addresses['home'] = full_address
        elif address_type == 'MAIL':
            addresses['mail'] = full_address


    # get citizenzhip
    db.execute("SELECT c.descrshort FROM " + db.table_prefix + "ps_citizenship cit, dbsastg.ps_country_tbl c WHERE emplid=%s AND cit.country=c.country", (str(emplid),))
    #if 'citizen' in p.config:
    #    del p.config['citizen']
    for country, in db:
        data['citizen'] = country

    # get Canadian visa status
    # sorting by effdt to get the latest in the dictionary
    db.execute("SELECT t.descrshort FROM dbsastg.ps_visa_pmt_data v, " + db.table_prefix + "ps_visa_permit_tbl t WHERE emplid=%s AND v.visa_permit_type=t.visa_permit_type AND v.country=t.country AND v.country='CAN' AND v.visa_wrkpmt_status='A' AND t.eff_status='A' ORDER BY v.effdt ASC", (str(emplid),))
    #if 'visa' in p.config:
    #    del p.config['visa']
    for desc, in db:
        data['visa'] = desc

    # emails
    #execute_query(db, "SELECT e_addr_type, email_addr, pref_email_flag FROM " + db.table_prefix + "ps_email_addresses c WHERE emplid=%s", (str(emplid),))
    #for e_addr_type, email_addr, pref_email_flag in iter_rows(db):
    #    print (e_addr_type, email_addr, pref_email_flag)
    
    # other stuff from ps_personal_data
    db.execute('SELECT sex FROM ' + db.table_prefix + 'ps_personal_data WHERE emplid=%s', (str(emplid),))
    #if 'gender' in p.config:
    #    del p.config['gender']
    for sex, in db:
        if sex:
            data['gender'] = sex # 'M', 'F', 'U'    
    
    return data


