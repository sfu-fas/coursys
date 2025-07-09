from coredata.models import Person, Semester, SemesterWeek, CourseOffering
from django.conf import settings
from django.core.mail import mail_admins
import django.db.transaction
from django.core.cache import cache
from django.utils.html import conditional_escape as e
import re, hashlib, datetime, string, urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse, http.client, time, json
import socket, decimal


multiple_breaks = re.compile(r'\n\n+')


class DBConn(object):
    """
    Singleton object representing DB connection. Implements a big enough subset of PEP 249 for me.
    
    singleton pattern implementation from: http://stackoverflow.com/questions/42558/python-and-the-singleton-pattern
    
    Absolutely NOT thread safe.
    Implemented as a singleton to minimize number of times DB connection overhead occurs.
    Should only be created on-demand (in function) to minimize startup for other processes.
    """
    _instance = None
    def __new__(cls):
        if not cls._instance:
            cls._instance = super(DBConn, cls).__new__(cls)
        return cls._instance

    def __init__(self, verbose=False):
        self.conn, self.db = self.get_connection()
        self.verbose = verbose

    def get_connection(self):
        raise NotImplementedError
    def escape_arg(self, a):
        raise NotImplementedError

    def execute(self, query, args):
        "Execute a query, safely substituting arguments"
        # should be ensuring real/active connection here?
        clean_args = tuple((self.escape_arg(a) for a in args))
        real_query = query % clean_args
        if self.verbose:
            print(">>>", real_query)
        self.query = real_query
        return self.db.execute(real_query)

    def prep_value(self, v):
        "Transform a DB result value into the value we want."
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

    def fetchone(self):
        row = self.db.fetchone()
        if row is None:
            return row
        return tuple((self.prep_value(v) for v in row))


class SIMSConnMSSQL(DBConn):
    def get_connection(self):
        if settings.DISABLE_REPORTING_DB:
            raise SIMSProblem("Reporting database access has been disabled in this deployment.")

        import pyodbc
        try:
            dbconn = pyodbc.connect("DRIVER={FreeTDS};SERVER=%s;PORT=1433;DATABASE=%s;Trusted_Connection=Yes"
                                    % (settings.SIMS_DB_SERVER, settings.SIMS_DB_NAME))
        except (pyodbc.ProgrammingError, pyodbc.OperationalError):
            raise SIMSProblem("Unable to connect to reporting database.")
        cursor = dbconn.cursor()
        return dbconn, cursor

    # adapted from _quote_simple_value from _mssql.pyx https://github.com/pymssql/pymssql/blob/master/src/pymssql/_mssql.pyx#L1930-L1933
    def escape_arg(self, value, charset='utf8'):
        if type(value) in (tuple, list, set):
            return '(' + ', '.join((self.escape_arg(v) for v in value)) + ')'

        if value == None:
            return b'NULL'

        if isinstance(value, bool):
            return '1' if value else '0'

        if isinstance(value, float):
            return repr(value)#.encode(charset)

        if isinstance(value, (int, decimal.Decimal)):
            return str(value)#.encode(charset)

        #if isinstance(value, uuid.UUID):
        #    return _quote_simple_value(str(value))

        if isinstance(value, str):
            return ("N'" + value.replace("'", "''") + "'")#.encode(charset)

        #if isinstance(value, bytearray):
        #    return b'0x' + binascii.hexlify(bytes(value))

        #if isinstance(value, (str, bytes)):
        #    # see if it can be decoded as ascii if there are no null bytes
        #    if b'\0' not in value:
        #        try:
        #            value.decode('ascii')
        #            return b"'" + value.replace(b"'", b"''") + b"'"
        #        except UnicodeDecodeError:
        #            pass
        #    # Python 3: handle bytes
        #    # @todo - Marc - hack hack hack
        #    if isinstance(value, bytes):
        #        return b'0x' + binascii.hexlify(value)
        #    # will still be string type if there was a null byte in it or if the
        #    # decoding failed.  In this case, just send it as hex.
        #    if isinstance(value, str):
        #        return '0x' + value.encode('hex')

        if isinstance(value, datetime.datetime):
            return "'%04d-%02d-%02d %02d:%02d:%02d.%03d'" % (
                value.year, value.month, value.day,
                value.hour, value.minute, value.second,
                value.microsecond / 1000)

        if isinstance(value, datetime.date):
            return "'%04d-%02d-%02d'" % (
            value.year, value.month, value.day)

        return None

    def prep_value(self, v):
        """
        get result value into a useful format
        """
        if isinstance(v, str):
            return v.strip()
        elif isinstance(v, decimal.Decimal):
            return float(v)
        else:
            return v


class SIMSConnDB2(DBConn):
    """
    Singleton object representing SIMS DB connection
    """
    DatabaseError = ReferenceError # placeholder until we have the DB2 module
    DB2Error = ReferenceError

    def get_connection(self):
        if settings.DISABLE_REPORTING_DB:
            raise SIMSProblem("Reporting database access has been disabled in this deployment.")

        try:
            import ibm_db_dbi
        except ImportError:
            raise SIMSProblem("could not import DB2 module")
        SIMSConnDB2.DatabaseError = ibm_db_dbi.DatabaseError
        SIMSConnDB2.DB2Error = ibm_db_dbi.Error
        try:
            dbconn = ibm_db_dbi.connect(self.sims_db, self.sims_user, self.sims_passwd)
        except ibm_db_dbi.Error:
            raise #SIMSProblem("Could not communicate with reporting database.")
        cursor = dbconn.cursor()
        cursor.execute("SET SCHEMA "+self.schema)
        return dbconn, cursor

    def escape_arg(self, a):
        """
        Escape argument for DB2
        """
        # Based on description of PHP's db2_escape_string
        if type(a) in (int,int):
            return str(a)
        if type(a) in (tuple, list, set):
            return '(' + ', '.join((self.escape_arg(v) for v in a)) + ')'
        
        # assume it's a string if we don't know any better
        a = str(a)
        a = a.replace("\\", "\\\\")
        a = a.replace("'", "\\'")
        a = a.replace('"', '\\"')
        a = a.replace("\r", "\\r")
        a = a.replace("\n", "\\n")
        a = a.replace("\x00", "\\\x00")
        a = a.replace("\x1a", "\\\x1a")
        return "'" + a + "'"

    def prep_value(self, v):
        """
        get DB2 value into a useful format
        """
        if isinstance(v, str):
            return v.strip()
        elif isinstance(v, decimal.Decimal):
            return float(v)
        else:
            return v


class SIMSProblem(Exception):
    """
    Class used to pass back problems with the SIMS connection.
    """
    pass


def SIMS_problem_handler_MSSQL(func):
    """
    Decorator to deal somewhat gracefully with any SIMS database problems.
    Any decorated function may raise a SIMSProblem instance to indicate a
    problem with the database connection.

    Should be applied to any functions that use a SIMSConn object.
    """

    def wrapped(*args, **kwargs):
        import pyodbc
        # check for the types of errors we know might happen and return an error message in a SIMSProblem
        try:
            return func(*args, **kwargs)
        except pyodbc.ProgrammingError as e:
            raise SIMSProblem("reporting database error: " + str(e))

    wrapped.__name__ = func.__name__
    return wrapped


def SIMS_problem_handler_DB2(func):
    """
    Decorator to deal somewhat gracefully with any SIMS database problems.
    Any decorated function may raise a SIMSProblem instance to indicate a
    problem with the database connection.

    Should be applied to any functions that use a SIMSConn object.
    """
    def wrapped(*args, **kwargs):
        # check for the types of errors we know might happen and return an error message in a SIMSProblem
        try:
            return func(*args, **kwargs)
        except SIMSConn.DatabaseError as e:
            raise SIMSProblem("could not connect to reporting database")
        except SIMSConn.DB2Error as e:
            raise SIMSProblem("problem with connection to reporting database")

    wrapped.__name__ = func.__name__
    return wrapped


SIMSConn = SIMSConnMSSQL
SIMS_problem_handler = SIMS_problem_handler_MSSQL


def _args_to_key(args, kwargs):
    "Hash arguments to get a cache key"
    h = hashlib.new('md5')
    h.update(str(args).encode('utf8'))
    h.update(str(kwargs).encode('utf8'))
    return h.hexdigest()


def cache_by_args(func, seconds=38800): # 8 hours by default
    """
    Decorator to cache query results from SIMS (if successful: no SIMSProblem).
    Requires arguments that can be converted to strings that uniquely identifies the results.
    Return results must be pickle-able so they can be cached.
    """
    def wrapped(*args, **kwargs):
        key = "simscache-" + func.__name__ + "-" + _args_to_key(args, kwargs)
        # first check cache
        cacheres = cache.get(key)
        if cacheres:
            return cacheres
        
        # not in cache: calculate
        res = func(*args, **kwargs)

        # got a result (with no exception thrown): cache it
        cache.set(key, res, seconds)
        return res
    
    wrapped.__name__ = func.__name__
    return wrapped


@cache_by_args
def userid_from_sims(emplid):
    """
    Guess userid from campus email address. Can be wrong because of mail aliases?
    """
    db = SIMSConn()
    db.execute("SELECT E_ADDR_TYPE, EMAIL_ADDR, PREF_EMAIL_FLAG FROM PS_EMAIL_ADDRESSES C WHERE E_ADDR_TYPE='CAMP' AND EMPLID=%s", (str(emplid),))
    userid = None
    for _, email_addr, _ in db:
        if email_addr.endswith('@sfu.ca'):
            userid = email_addr[:-7]
        if userid and len(userid) > 8:
            userid = None
    return userid


@cache_by_args
@SIMS_problem_handler
def find_person(emplid, get_userid=True):
    """
    Find the person in SIMS: return data or None (not found) or may raise a SIMSProblem.
    """
    db = SIMSConn()
    db.execute("SELECT EMPLID, LAST_NAME, FIRST_NAME, MIDDLE_NAME FROM PS_PERSONAL_DATA WHERE EMPLID=%s",
               (str(emplid),))

    for emplid, last_name, first_name, middle_name in db:
        # use emails to guess userid: if not found, leave unset and hope the userid API has it on next nightly update
        if get_userid:
            userid = userid_from_sims(emplid)
        else:
            userid = None
        return {'emplid': emplid, 'last_name': last_name, 'first_name': first_name, 'middle_name': middle_name, 'userid': userid}


@cache_by_args
@SIMS_problem_handler
def find_external_email(emplid):
    db = SIMSConn()
    db.execute("SELECT EMAIL_ADDR FROM PS_EMAIL_ADDRESSES WHERE EMPLID=%s AND E_ADDR_TYPE='WORK'",
               (str(emplid),))
    row = db.fetchone()
    if row and not row[0].endswith('sfu.ca'):
        return row[0]


def add_person(emplid, commit=True, get_userid=True, external_email=False):
    """
    Add a Person object based on the found SIMS data
    """
    with django.db.transaction.atomic():
        ps = Person.objects.filter(emplid=emplid)
        if ps:
            # person already there: ignore
            return ps[0]

        data = find_person(emplid, get_userid=get_userid)
        if not data:
            return

        p = Person(emplid=data['emplid'], last_name=data['last_name'], first_name=data['first_name'],
                   pref_first_name=data['first_name'], middle_name=data['middle_name'], userid=data['userid'])

        if external_email:
            # used for fetching grad committee members: includes non-SFU people and we want
            # their non-SFU email address
            e = find_external_email(emplid)
            if e:
                p.config['external_email'] = e

        if data['userid']:
            ps = Person.objects.filter(userid=data['userid'])
            if ps:
                raise ValueError('Possibly re-used userid %r?' % (data['userid']))

        if commit:
            p.save()
    return p


@cache_by_args
def get_person_by_userid(userid):
    return ensure_person_from_userid(userid)


@cache_by_args
@SIMS_problem_handler
def get_names(emplid):
    """
    Basic personal info to populate Person object
    
    Returns (last_name, first_name, middle_name, pref_first_name, title).
    """
    db = SIMSConn()
    
    #userid = userid_from_sims(emplid)
    last_name = None
    first_name = None
    middle_name = None
    pref_first_name = None
    title = None
    
    db.execute("SELECT NAME_TYPE, NAME_PREFIX, LAST_NAME, FIRST_NAME, MIDDLE_NAME FROM PS_NAMES WHERE "
               "EMPLID=%s AND EFF_STATUS='A' AND NAME_TYPE IN ('PRI','PRF') "
               "ORDER BY EFFDT", (str(emplid),))
    # order by effdt to leave the latest in the dictionary at end
    for name_type, prefix, last, first, middle in db:
        if name_type == 'PRI':
            first_name = first
        elif name_type == 'PRF':
            pref_first_name = first
        # Use most-recent last/middle from either PRI or PRF,
        # whichever is most recent. Seems to be what SIMS does.
        last_name = last
        middle_name = middle
        title = prefix
    
    return last_name, first_name, middle_name, pref_first_name, title


GRADFIELDS = ['ccredits', 'citizen', 'gpa', 'gender', 'visa']
@cache_by_args
@SIMS_problem_handler
def grad_student_info(emplid):
    "The info we want in Person.config for all GradStudents"
    return more_personal_info(emplid, needed=GRADFIELDS)


PLAN_QUERY = string.Template("""
            SELECT PROG.EMPLID, PLANTBL.ACAD_PLAN, PLANTBL.DESCR, PLANTBL.TRNSCR_DESCR
            FROM PS_ACAD_PROG AS PROG
                INNER JOIN PS_ACAD_PLAN AS APLAN
                    ON (PROG.EMPLID=APLAN.EMPLID AND PROG.ACAD_CAREER=APLAN.ACAD_CAREER
                        AND PROG.STDNT_CAR_NBR=APLAN.STDNT_CAR_NBR AND PROG.EFFDT=APLAN.EFFDT AND PROG.EFFSEQ=APLAN.EFFSEQ)
                INNER JOIN PS_ACAD_PLAN_TBL AS PLANTBL ON (PLANTBL.ACAD_PLAN=APLAN.ACAD_PLAN)
            WHERE 
              PROG.EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PROG WHERE EMPLID=PROG.EMPLID AND ACAD_CAREER=PROG.ACAD_CAREER AND STDNT_CAR_NBR=PROG.STDNT_CAR_NBR AND EFFDT <= GETDATE())
              AND PROG.EFFSEQ=(SELECT MAX(EFFSEQ) FROM PS_ACAD_PROG WHERE EMPLID=PROG.EMPLID AND ACAD_CAREER=PROG.ACAD_CAREER AND STDNT_CAR_NBR=PROG.STDNT_CAR_NBR AND EFFDT=PROG.EFFDT)
              AND PLANTBL.EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PLAN_TBL WHERE ACAD_PLAN=PLANTBL.ACAD_PLAN AND EFF_STATUS='A' AND EFFDT<=GETDATE())
              AND PROG.PROG_STATUS='AC' AND PLANTBL.EFF_STATUS='A'
              AND $where
            ORDER BY PROG.EMPLID, APLAN.PLAN_SEQUENCE""")


SUBPLAN_QUERY = string.Template("""
            SELECT PROG.EMPLID, PLANTBL.ACAD_SUB_PLAN, PLANTBL.DESCR, PLANTBL.TRNSCR_DESCR
            FROM PS_ACAD_PROG PROG, PS_ACAD_SUBPLAN SPLAN, PS_ACAD_SUBPLN_TBL AS PLANTBL
            WHERE PROG.EMPLID=SPLAN.EMPLID AND PROG.STDNT_CAR_NBR=SPLAN.STDNT_CAR_NBR AND PROG.EFFDT=SPLAN.EFFDT AND PROG.EFFSEQ=SPLAN.EFFSEQ
              AND PLANTBL.ACAD_PLAN=SPLAN.ACAD_PLAN AND PLANTBL.ACAD_SUB_PLAN=SPLAN.ACAD_SUB_PLAN
              AND PROG.EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PROG WHERE EMPLID=PROG.EMPLID AND ACAD_CAREER=PROG.ACAD_CAREER AND STDNT_CAR_NBR=PROG.STDNT_CAR_NBR AND EFFDT <= GETDATE())
              AND PROG.EFFSEQ=(SELECT MAX(EFFSEQ) FROM PS_ACAD_PROG WHERE EMPLID=PROG.EMPLID AND ACAD_CAREER=PROG.ACAD_CAREER AND STDNT_CAR_NBR=PROG.STDNT_CAR_NBR AND EFFDT=PROG.EFFDT)
              AND PLANTBL.EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PLAN_TBL WHERE ACAD_PLAN=PLANTBL.ACAD_PLAN AND EFF_STATUS='A' AND EFFDT<=GETDATE())
              AND PROG.PROG_STATUS='AC' AND PLANTBL.EFF_STATUS='A'
              AND $where
            ORDER BY PROG.EMPLID""")


ALLFIELDS = 'alldata'
@cache_by_args
@SIMS_problem_handler
def more_personal_info(emplid, needed=ALLFIELDS, exclude=[]):
    """
    Get contact info for student: return data or None (not found) or a SIMSProblem instance (error message).
    
    Returns the same dictionary format as Person.config (for the fields it finds).
    
    needed is a list containing the values needed in the result (if available), or ALLFIELDS
    """
    db = SIMSConn()
    data = {}
    
    # get phone numbers
    if (needed == ALLFIELDS or 'phones' in needed) and 'phones' not in exclude:
        db.execute('SELECT PHONE_TYPE, COUNTRY_CODE, PHONE, EXTENSION, PREF_PHONE_FLAG FROM PS_PERSONAL_PHONE WHERE EMPLID=%s', (str(emplid),))
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
    if (needed == ALLFIELDS or 'addresses' in needed) and 'addresses' not in exclude:
        # sorting by effdt to get the latest in the dictionary
        db.execute("SELECT ADDRESS_TYPE, EFFDT, EFF_STATUS, C.DESCRSHORT, ADDRESS1, ADDRESS2, ADDRESS3, ADDRESS4, CITY, STATE, POSTAL FROM PS_ADDRESSES A, PS_COUNTRY_TBL C WHERE EMPLID=%s AND EFF_STATUS='A' AND A.COUNTRY=C.COUNTRY ORDER BY EFFDT ASC", (str(emplid),))
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
    if (needed == ALLFIELDS or 'citizen' in needed) and 'citizen' not in exclude:
        db.execute("SELECT C.DESCRSHORT FROM PS_CITIZENSHIP CIT, PS_COUNTRY_TBL C WHERE EMPLID=%s AND CIT.COUNTRY=C.COUNTRY", (str(emplid),))
        #if 'citizen' in p.config:
        #    del p.config['citizen']
        for country, in db:
            data['citizen'] = country

    # get Canadian visa status
    if (needed == ALLFIELDS or 'visa' in needed) and 'visa' not in exclude:
        # sorting by effdt to get the latest in the dictionary
        db.execute("SELECT T.DESCRSHORT FROM PS_VISA_PMT_DATA V, PS_VISA_PERMIT_TBL T WHERE EMPLID=%s AND V.VISA_PERMIT_TYPE=T.VISA_PERMIT_TYPE AND V.COUNTRY=T.COUNTRY AND V.COUNTRY='CAN' AND V.VISA_WRKPMT_STATUS='A' AND T.EFF_STATUS='A' ORDER BY V.EFFDT ASC", (str(emplid),))
        #if 'visa' in p.config:
        #    del p.config['visa']
        for desc, in db:
            data['visa'] = desc

    # emails
    #execute_query(db, "SELECT e_addr_type, email_addr, pref_email_flag FROM ps_email_addresses c WHERE emplid=%s", (str(emplid),))
    #for e_addr_type, email_addr, pref_email_flag in iter_rows(db):
    #    print (e_addr_type, email_addr, pref_email_flag)
    
    # other stuff from ps_personal_data
    if (needed == ALLFIELDS or 'gender' in needed) and 'gender' not in exclude:
        db.execute('SELECT SEX FROM PS_PERSONAL_DATA WHERE EMPLID=%s', (str(emplid),))
        #if 'gender' in p.config:
        #    del p.config['gender']
        for sex, in db:
            if sex:
                data['gender'] = sex  # should match keys from coredata.models.GENDER_DESCR
    
    # academic programs
    if (needed == ALLFIELDS or 'programs' in needed) and 'programs' not in exclude:
        programs = []
        data['programs'] = programs
        db.execute(PLAN_QUERY.substitute({'where': 'PROG.EMPLID=%s'}), (str(emplid),))
        #  AND apt.trnscr_print_fl='Y'
        for emplid, acad_plan, descr, transcript in db:
            label = transcript or descr
            prog = "%s (%s)" % (label, acad_plan)
            programs.append(prog)

        # also add academic subplans
        db.execute(SUBPLAN_QUERY.substitute({'where': 'PROG.EMPLID=%s'}), (str(emplid),))
        for emplid, subplan, descr, transcript in db:
            label = transcript or descr
            prog = "%s (%s subplan)" % (label, subplan)
            programs.append(prog)



    # GPA and credit count
    if (needed == ALLFIELDS or 'gpa' in needed or 'ccredits' in needed) and 'ccredits' not in exclude:
        db.execute('SELECT CUM_GPA, TOT_CUMULATIVE FROM PS_STDNT_CAR_TERM WHERE EMPLID=%s ORDER BY STRM DESC  OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY', (str(emplid),))
        data['gpa'] = 0.0
        data['ccredits'] = 0
        for gpa, cred in db:
            data['gpa'] = gpa
            data['ccredits'] = cred

    return data


@cache_by_args
@SIMS_problem_handler
def more_course_info(course):
    """
    More info about a course (for the advisor portal) 
    """
    offerings = CourseOffering.objects.filter(course=course).exclude(crse_id__isnull=True).order_by('-semester__name')
    if offerings:
        offering = offerings[0]
    else:
        return None
    return more_offering_info(offering, browse_data=False)

@cache_by_args
@SIMS_problem_handler
def more_offering_info(offering, browse_data=False, offering_effdt=False):
    """
    More info about a course offering (for the course browser) 
    """
    db = SIMSConn()
    req_map = get_reqmnt_designtn()

    data = {}
    crse_id = "%06i" % (offering.crse_id)
    eff_where = ''
    if offering_effdt:
        effdt = offering.semester.start
        eff_where = "AND EFFDT<=%s" % (db.escape_arg(effdt.isoformat()))

    db.execute("""
        SELECT DESCR, SSR_COMPONENT, COURSE_TITLE_LONG, DESCRLONG
        FROM PS_CRSE_CATALOG
        WHERE EFF_STATUS='A' AND CRSE_ID=%s """ + eff_where + """
        ORDER BY EFFDT DESC  OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY""", (crse_id,))
    for shorttitle, component, longtitle, descrlong in db:
        data['shorttitle'] = e(shorttitle)
        data['component'] = e(component)
        data['longtitle'] = e(longtitle)
        data['descrlong'] = e(descrlong)
        #data['rqmnt_designtn'] = e(req_map.get(rqmnt_designtn, 'none'))

    if browse_data and 'shorttitle' in data:
        del data['shorttitle']
    
    if not data:
        return None

    return data



@cache_by_args
def crse_id_info(crse_id):
    """
    More info we need about this crse_id. Separate function so it can easily be cached.
    """
    db = SIMSConn()
    offering_query = "SELECT O.SUBJECT, O.CATALOG_NBR, C.DESCR FROM PS_CRSE_OFFER O, PS_CRSE_CATALOG C WHERE O.CRSE_ID=C.CRSE_ID AND O.CRSE_ID=%s ORDER BY O.EFFDT DESC, C.EFFDT DESC  OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY"
    db.execute(offering_query, (crse_id,))
    fields = ['subject', 'catalog_nbr', 'descr']
    for row in db:
        cdata = dict(list(zip(fields, row)))
        cdata['crse_found'] = True
        return cdata
    return {'subject': '?', 'catalog_nbr': '?', 'descr': '?', 'crse_found': False}

@cache_by_args
def ext_org_info(ext_org_id):
    """
    More info we need about this external org. Separate function so it can easily be cached.
    """
    db = SIMSConn()
    ext_org_query = "SELECT E.DESCR FROM PS_EXT_ORG_TBL E WHERE E.EFF_STATUS='A' AND E.EXT_ORG_ID=%s ORDER BY EFFDT DESC  OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY"
    db.execute(ext_org_query, (ext_org_id,))
    fields = ['ext_org']
    for row in db:
        cdata = dict(list(zip(fields, row)))
        return cdata
    return {'ext_org': '?'}


REQMNT_DESIGNTN_FLAGS = { # map of ps_rqmnt_desig_tbl.descrshort to CourseOffering WQB fields
    '': [],
    'W': ['write'],
    'Q': ['quant'],
    'B-Hum': ['bhum'],
    'B-Sci': ['bsci'],
    'B-Soc': ['bsoc'],
    'W/Q': ['write', 'quant'],
    'W/B-Hum': ['write', 'bhum'],
    'W/B-Sci': ['write', 'bsci'],
    'W/B-Soc': ['write', 'bsoc'],
    'Q/B-Soc': ['quant', 'bsoc'],
    'Q/B-Sci': ['quant', 'bsci'],
    'B-Hum/Sci': ['bhum', 'bsci'],
    'B-H/Soc/Sc': ['bhum', 'bsoc', 'bsci'],
    'B-Soc/Sci': ['bsoc', 'bsci'],
    'W/Q/B-Sci': ['write', 'quant', 'bsci'],
    'W/B-HumSci': ['bhum', 'bsci'],
    'B-Hum/Soc': ['bhum', 'bsoc'],
    'W/B-H/Soc': ['write', 'bhum', 'bsoc'],
    'Q/B-Soc/Sc': ['quant', 'bsoc', 'bsci'],
    }

@cache_by_args
def get_reqmnt_designtn():
    """
    Get and cache requirement designations (to avoid joining yet another table).
    """
    db = SIMSConn()
    
    db.execute("""SELECT R.RQMNT_DESIGNTN, R.DESCRSHORT FROM PS_RQMNT_DESIG_TBL R
        WHERE R.EFFDT=(SELECT MAX(EFFDT) FROM PS_RQMNT_DESIG_TBL
                       WHERE RQMNT_DESIGNTN=R.RQMNT_DESIGNTN AND R.EFFDT<=GETDATE() AND EFF_STATUS='A')
            AND R.EFF_STATUS='A'""", ())
    return dict(db)

@SIMS_problem_handler
def get_waitlist_info(offering, date=None):
    """
    Get waitlist movement info for a given course offering, for the prior day
    """
    if not date:
        date = datetime.date.today()
    date = date - datetime.timedelta(days=1)

    db = SIMSConn()

    enrl_drp = None
    wait_drp = None
    wait_add = None

    query = """
        SELECT COALESCE(D1.STUDENT_DROP, 0) AS S_DROP, COALESCE(D2.STUDENT_DRWL, 0) AS S_DRWL, COALESCE(D3.STUDENT_FULL, 0) AS S_FULL
        FROM (
            SELECT %s AS CLASS_NBR, %s AS STRM, %s AS STATUS_DATE
            ) D0
            LEFT OUTER JOIN (
            SELECT CT.CLASS_NBR, E.STRM, E.ENRL_STATUS_REASON, COUNT(E.EMPLID) AS STUDENT_DROP
                FROM PS_STDNT_ENRL E 
                JOIN PS_CLASS_TBL CT ON E.CLASS_NBR = CT.CLASS_NBR AND E.STRM = CT.STRM
                WHERE CT.CLASS_NBR = %s AND E.STRM = %s AND E.ENRL_STATUS_REASON IN ('DROP') AND E.LAST_DROP_DT_STMP = %s
                GROUP BY CT.CLASS_NBR, E.STRM, E.ENRL_STATUS_REASON
            ) D1 ON D0.CLASS_NBR = D1.CLASS_NBR AND D0.STRM = D1.STRM
            LEFT OUTER JOIN (
            SELECT CT.CLASS_NBR, E.STRM, E.ENRL_STATUS_REASON, COUNT(E.EMPLID) AS STUDENT_DRWL
                FROM PS_STDNT_ENRL E 
                JOIN PS_CLASS_TBL CT ON E.CLASS_NBR = CT.CLASS_NBR AND E.STRM = CT.STRM
                WHERE CT.CLASS_NBR = %s AND E.STRM = %s AND E.ENRL_STATUS_REASON IN ('DRWL') AND E.LAST_DROP_DT_STMP = %s
                GROUP BY CT.CLASS_NBR, E.STRM, E.ENRL_STATUS_REASON
            ) D2 ON D0.CLASS_NBR = D2.CLASS_NBR AND D0.STRM = D2.STRM
            LEFT OUTER JOIN (
            SELECT CT.CLASS_NBR, E.STRM, E.ENRL_STATUS_REASON, COUNT(E.EMPLID) AS STUDENT_FULL
                FROM PS_STDNT_ENRL E 
                JOIN PS_CLASS_TBL CT ON E.CLASS_NBR = CT.CLASS_NBR AND E.STRM = CT.STRM
                WHERE CT.CLASS_NBR = %s AND E.STRM = %s AND E.ENRL_STATUS_REASON IN ('FULL') AND E.LAST_ENRL_DT_STMP = %s
                GROUP BY CT.CLASS_NBR, E.STRM, E.ENRL_STATUS_REASON
            ) D3 ON D0.CLASS_NBR = D3.CLASS_NBR AND D0.STRM = D3.STRM
        """
    
    db.execute(query, (offering.class_nbr, offering.semester.name, date) * 4)

    for S_DROP, S_DRWL, S_FULL in db:
        enrl_drp = S_DROP
        wait_drp = S_DRWL
        wait_add = S_FULL

    return enrl_drp, wait_drp, wait_add


@cache_by_args
def get_semester_names():
    """
    Get and cache semester names (to avoid joining yet another table).
    """
    db = SIMSConn()
    
    db.execute("SELECT T.STRM, T.DESCR FROM PS_TERM_TBL T", ())
    return dict(db)
    
@cache_by_args
@SIMS_problem_handler
def course_data(emplid, needed=ALLFIELDS, exclude=[]):
    """
    Get course and GPA info for light transcript display
    """
    data = {}
    emplid = str(emplid)
    req_map = get_reqmnt_designtn()
    sem_name = get_semester_names()
    db = SIMSConn()
    
    # match trns_crse_sch and trns_crse_dtl by their many keys
    crse_join = "T.EMPLID=S.EMPLID AND T.ACAD_CAREER=S.ACAD_CAREER AND T.INSTITUTION=S.INSTITUTION AND T.MODEL_NBR=S.MODEL_NBR"
    
    # transfers
    transfer_query = "SELECT T.CRSE_ID, T.CRSE_GRADE_OFF, T.UNT_TRNSFR, T.REPEAT_CODE, T.ARTICULATION_TERM, " \
                     " T.RQMNT_DESIGNTN, S.EXT_ORG_ID, S.SRC_ORG_NAME " \
                     "FROM PS_TRNS_CRSE_DTL T, PS_TRNS_CRSE_SCH S " \
                     "WHERE " + crse_join + " AND T.EMPLID=%s"
    db.execute(transfer_query, (emplid,))
    transfers = []
    data['transfers'] = transfers
    fields = ['crse_id', 'grade', 'units', 'repeat', 'strm', 'reqdes', 'ext_org_id', 'src_org']
    for row in list(db):
        rdata = dict(list(zip(fields, row)))
        crse_id = rdata['crse_id']
        ext_org_id = rdata['ext_org_id']
        
        rdata.update(crse_id_info(crse_id))
        if not rdata['crse_found']:
            #print rdata
            continue

        if rdata['reqdes']:
            rdata['req'] = req_map[rdata['reqdes']]
        else:
            rdata['req'] = ''

        if not rdata['src_org']:
            rdata.update(ext_org_info(ext_org_id))
        rdata['src'] = rdata['src_org'] or rdata['ext_org']

        del rdata['src_org']
        if 'ext_org' in rdata:
            del rdata['ext_org']
        del rdata['ext_org_id']
        del rdata['reqdes']
        transfers.append(rdata)
    
    transfers.sort(key=lambda k: (k['subject'], k['catalog_nbr']))

    # active semesters
    term_query = "SELECT T.STRM, T.ACAD_CAREER, T.TOT_PASSD_PRGRSS, T.CUR_GPA, T.CUM_GPA, S.ACAD_STNDNG_ACTN, G.LS_GPA " \
                 "FROM PS_STDNT_CAR_TERM T " \
                 " LEFT JOIN PS_ACAD_STDNG_ACTN S ON T.EMPLID=S.EMPLID AND T.STRM=S.STRM " \
                 " LEFT JOIN PS_STDNT_SPCL_GPA G ON T.EMPLID=G.EMPLID AND T.STRM=G.STRM " \
                 "WHERE T.EMPLID=%s AND (G.GPA_TYPE='UGPA' OR G.GPA_TYPE IS NULL) " \
                 "ORDER BY T.STRM, S.EFFDT DESC, S.EFFSEQ DESC"
    db.execute(term_query, (emplid,))
    semesters = []
    semester_lookup = {}
    found = set()
    data['semesters'] = semesters
    fields = ['strm', 'career', 'units_passed', 'tgpa', 'cgpa', 'standing', 'udgpa']
    for row in db:
        rdata = dict(list(zip(fields, row)))
        strm = rdata['strm']
        if strm in found:
            # handle multiple rows from ps_acad_stdng_actn
            continue
        found.add(strm)
        rdata['courses'] = []
        rdata['semname'] = sem_name[strm]
        semesters.append(rdata)
        semester_lookup[strm] = rdata
        
    
    # courses
    enrl_query = "SELECT E.STRM, E.CLASS_NBR, E.UNT_TAKEN, " \
                 "E.REPEAT_CODE, E.CRSE_GRADE_OFF, E.RQMNT_DESIGNTN, " \
                 "C.SUBJECT, C.CATALOG_NBR, C.DESCR " \
                 "FROM PS_STDNT_ENRL E, PS_CLASS_TBL C " \
                 "WHERE E.CLASS_NBR=C.CLASS_NBR AND E.STRM=C.STRM AND E.EMPLID=%s " \
                 "AND C.CLASS_TYPE='E' AND E.STDNT_ENRL_STATUS='E' " \
                 "ORDER BY E.STRM, C.SUBJECT, C.CATALOG_NBR"
    db.execute(enrl_query, (emplid,))
    fields = ['strm', 'class_nbr', 'unit_taken', 'repeat', 'grade', 'reqdes', 'subject', 'number', 'descr']
    
    for row in db:
        rdata = dict(list(zip(fields, row)))
        strm = rdata['strm']
        if rdata['reqdes']:
            rdata['req'] = req_map[rdata['reqdes']]
        else:
            rdata['req'] = ''

        del rdata['reqdes']
        if strm in semester_lookup:
            semester_lookup[strm]['courses'].append(rdata)
    
    return data


@cache_by_args
@SIMS_problem_handler
def transfer_data(emplid):
    """
    Return external transfer credits for a given emplid

    :param string emplid: The employee ID of the person whose transfer info we want
    :return: A JSON-fiable object with external transfers
    :rtype: object
    """
    emplid = str(emplid)
    db = SIMSConn()
    transfers = "WITH CRSE_OFFER AS (SELECT CRSE_ID, CRSE_OFFER_NBR, SUBJECT, CATALOG_NBR FROM PS_CRSE_OFFER "\
                "A WHERE EFFDT=(SELECT MAX(EFFDT) FROM PS_CRSE_OFFER WHERE CRSE_ID=A.CRSE_ID)), EXT_ORG_TBL AS"\
                "(SELECT EXT_ORG_ID, DESCR50 FROM PS_EXT_ORG_TBL A WHERE EFFDT=(SELECT MAX(EFFDT) FROM"\
                " PS_EXT_ORG_TBL WHERE EXT_ORG_ID=A.EXT_ORG_ID))"\
                "SELECT TCD.EMPLID, EOT.DESCR50, EC.SCHOOL_SUBJECT, EC.SCHOOL_CRSE_NBR, TCD.TRNSFR_EQVLNCY_GRP, "\
                "TCD.TRNSFR_STAT, CO.SUBJECT, CO.CATALOG_NBR, TCD.CRSE_GRADE_INPUT AS TCD_GRADE_INPUT, "\
                "TCD.CRSE_GRADE_OFF AS TCD_GRADE_OFF,EC.CRSE_GRADE_INPUT AS EC_GRADE_INPUT, EC.CRSE_GRADE_OFF "\
                "AS EC_GRADE_OFF, TCD.UNT_TRNSFR "\
                "FROM PS_TRNS_CRSE_DTL TCD INNER JOIN PS_TRNS_CRSE_SCH TCS ON TCS.EMPLID=TCD.EMPLID "\
                "AND TCD.ACAD_CAREER=TCS.ACAD_CAREER AND TCD.INSTITUTION=TCS.INSTITUTION AND "\
                "TCD.MODEL_NBR=TCS.MODEL_NBR LEFT OUTER JOIN PS_EXT_COURSE EC ON EC.EMPLID=TCD.EMPLID AND "\
                "EC.EXT_COURSE_NBR=TCD.EXT_COURSE_NBR AND EC.EXT_ORG_ID=TCS.EXT_ORG_ID LEFT OUTER JOIN EXT_ORG_TBL "\
                "EOT ON TCD.TRNSFR_SRC_ID = EOT.EXT_ORG_ID LEFT OUTER JOIN CRSE_OFFER CO ON TCD.CRSE_ID = CO.CRSE_ID "\
                "AND TCD.CRSE_OFFER_NBR = CO.CRSE_OFFER_NBR WHERE TCD.TRNSFR_STAT='P' AND TCS.MODEL_STATUS='P' "\
                "AND TCD.EMPLID=%s ORDER BY TCD.MODEL_NBR, TCD.TRNSFR_EQVLNCY_GRP, TCD.TRNSFR_EQVLNCY_SEQ"
    db.execute(transfers, (emplid,))
    fields = ['emplid', 'descr', 'school_subject', 'crse_nbr', 'trsnf_equivlncy_grp', 'transfr_stat', 'subject',
              'catalog_nbr', 'tcd_grade_input', 'tcd_grade_off', 'ec_grade_input', 'ec_grade_off', 'unt_trnsfr']
    data = {}
    transfers = []
    for row in list(db):
        rdata = dict(list(zip(fields, row)))
        transfers.append(rdata)
    data['transfers'] = transfers
    return data


@cache_by_args
@SIMS_problem_handler
def classes_data(emplid):
    """
    Return all courses and grades taken by a given emplid

    :param string emplid: The employee ID of the person whose course info we want
    :return: A JSON-fiable object of courses taken
    :rtype: object
    """
    emplid = str(emplid)
    db = SIMSConn()
    courses = "SELECT E.STRM, C.SUBJECT, C.CATALOG_NBR, C.DESCR, E.CRSE_GRADE_OFF, E.UNT_TAKEN "\
                 "FROM PS_STDNT_ENRL E, PS_CLASS_TBL C "\
                 "WHERE E.CLASS_NBR=C.CLASS_NBR AND E.STRM=C.STRM AND E.EMPLID=%s "\
                 "AND C.CLASS_TYPE='E' AND E.STDNT_ENRL_STATUS='E' "\
                 "ORDER BY E.STRM, C.SUBJECT, C.CATALOG_NBR"
    db.execute(courses, (emplid,))
    fields = ['strm', 'subject', 'catalog_nbr', 'descr', 'crse_grade_off', 'unt_taken']
    data = {}
    courses = []
    for row in list(db):
        rdata = dict(list(zip(fields, row)))
        courses.append(rdata)
    data['courses'] = courses
    return data


@cache_by_args
@SIMS_problem_handler
def acad_plan_count(acad_plan, strm):
    """
    Return number of majors in academic plan (e.g. 'CMPTMAJ') in the semester or a SIMSProblem instance (error message).
    """
    db = SIMSConn()

    # most recent acad_plan, most recent acad_plan *in this program* for each student active this semester
    last_prog_plan = """(
        SELECT AP.EMPLID, MAX(AP.EFFDT) AS EFFDTPROG, MAX(AP2.EFFDT) AS EFFDT
        FROM PS_ACAD_PLAN AP
            INNER JOIN PS_ACAD_PLAN AP2 ON (AP.EMPLID=AP2.EMPLID)
            INNER JOIN PS_STDNT_CAR_TERM CT ON (AP.EMPLID=CT.EMPLID AND CT.STDNT_CAR_NBR=AP.STDNT_CAR_NBR )
        WHERE CT.STRM=%s AND AP.ACAD_PLAN=%s
        GROUP BY AP.EMPLID
    )"""

    # select those whose most recent program is in this acad_plan
    db.execute("SELECT COUNT(*) FROM " + last_prog_plan + " WHERE EFFDTPROG=EFFDT", (strm, acad_plan))
    return db.fetchone()[0]
    #for row in db:
    #    print row



@cache_by_args
@SIMS_problem_handler
def get_or_create_semester(strm):
    if not (isinstance(strm, str) and strm.isdigit() and len(strm)==4):
        raise ValueError("Bad strm: " + repr(strm))
    oldsem = Semester.objects.filter(name=strm)
    if oldsem:
        return oldsem[0]

    db = SIMSConn()
    db.execute("SELECT STRM, TERM_BEGIN_DT, TERM_END_DT FROM PS_TERM_TBL WHERE STRM=%s", (strm,))
    row = db.fetchone()
    if row is None:
        raise ValueError("Not Found: %r" % strm)
    strm, st, en = row
    
    # create Semester object
    sem = Semester(name=strm, start=st, end=en)
    sem.save()
    
    # also create SemesterWeek object for the first week
    first_monday = st
    while first_monday.weekday() != 0:
        first_monday += datetime.timedelta(days=1)    
    wk = SemesterWeek(semester=sem, week=1, monday=first_monday)
    wk.save()
    
    return sem



# queries for grad progress reports
@cache_by_args
@SIMS_problem_handler
def grad_student_courses(emplid):
    db = SIMSConn()
    query = "SELECT E.STRM, C.SUBJECT, C.CATALOG_NBR, C.CLASS_SECTION, C.CLASS_NBR, " \
                 "E.UNT_TAKEN, E.CRSE_GRADE_OFF, E.GRADE_POINTS " \
                 "FROM PS_STDNT_ENRL E INNER JOIN PS_CLASS_TBL C ON (E.CLASS_NBR=C.CLASS_NBR AND E.STRM=C.STRM) " \
                 "WHERE E.EMPLID=%s " \
                 "AND C.CLASS_TYPE='E' AND E.STDNT_ENRL_STATUS='E' AND E.ACAD_CAREER='GRAD' " \
                 "ORDER BY E.STRM, C.SUBJECT, C.CATALOG_NBR"
    db.execute(query, (str(emplid),))
    res = []
    for strm, subject, number, section, class_nbr, units, grade, gradepoints in db:
        offerings = CourseOffering.objects.filter(semester__name=strm, class_nbr=class_nbr).exclude(component='CAN')
        if offerings:
            instr = offerings[0].instructors_str()
        else:
            instr = ''
        res.append((strm, subject, number, section, units, grade, gradepoints, instr))

    return res

@cache_by_args
@SIMS_problem_handler
def grad_student_gpas(emplid):
    db = SIMSConn()
    query = "SELECT T.STRM, T.CUR_GPA, T.CUM_GPA " \
                 "FROM PS_STDNT_CAR_TERM T " \
                 "WHERE T.EMPLID=%s AND T.ACAD_CAREER='GRAD'"
    db.execute(query, (str(emplid),))
    return list(db)

# helper functions
def lazy_next_semester(semester):
    return offset_semester_string(semester, 1)

def offset_semester_string(semester, offset=1):
    return str(Semester.objects.get(name=semester).offset(offset).name)

def pairs( lst ):
    if len(lst) > 1:
        for i in range(1, len(lst)):
            yield (lst[i-1], lst[i])

#@cache_by_args
@SIMS_problem_handler
def get_timeline(emplid, verbose=False):
    """
        For the student with emplid, 
        Get a list of programs, start and end semester
        [{'program_code':'CPPHD', 'start':1111, 'end':1137, 'on leave':['1121', '1124']) ]
        
        * will include an 'adm_appl_nbr' if an admission record can be found with that program
    """
    programs = get_student_programs(emplid) 
    
    if verbose:
        print("----------")
        for program in programs:
            print(program)

    # calculate start and end date for programs
    prog_dict = {}
    for program_code, strm, unt_taken in programs: 
        if program_code not in prog_dict:
            prog_dict[program_code] = {'start':'9999', 'end':'1111', 'not_on_leave':[]}
        if int(strm) < int(prog_dict[program_code]['start']):
            prog_dict[program_code]['start'] = strm
        elif int(strm) > int(prog_dict[program_code]['end']):
            prog_dict[program_code]['end'] = strm
        if float(unt_taken) >= 0.1: 
            prog_dict[program_code]['not_on_leave'].append(strm)

    if verbose:
        print("----------")
        for key, val in prog_dict.items():
            print(key, val)

    # calculate on-leave semesters
    on_leave_semesters = [strm for strm, reason in get_on_leave_semesters(emplid)]

    try:
        for program_code, program_object in prog_dict.items():
            prog_dict[program_code]['on_leave'] = []
            semesters = Semester.range( program_object['start'], program_object['end'] )
            for semester in semesters:
                if (int(semester) <= int(Semester.current().name) and
                    (semester in on_leave_semesters or 
                    semester not in program_object['not_on_leave'])):
                    prog_dict[program_code]['on_leave'].append(semester)
            prog_dict[program_code]['on_leave'].sort()
    except Semester.DoesNotExist:
        print("Semester out of range", program_object['start'], program_object['end'])
        return {}

    # put the programs in a list, sorted by start date
    programs = []
    for program_code, program_object in prog_dict.items():
        del program_object['not_on_leave']
        program_object['program_code'] = program_code
        programs.append(program_object) 
    programs = sorted( programs, key= lambda x : int(x['start']) )

    if verbose: 
        print("----------")
        for program in programs:
            print(program)

    # how did it end?
    for program in programs:
        hdie = get_end_of_degree(emplid, program['program_code'], program['start'])
        if hdie: 
            program['how_did_it_end'] = { 'code':hdie[0], 
                                          'reason':hdie[1],
                                          'date':hdie[2],
                                          'semester': str(Semester.get_semester(hdie[2]).name) } 
            if int(program['how_did_it_end']['semester']) < int(program['end']):
                program['end'] = program['how_did_it_end']['semester']
        
    # for every previous program, create an end-date and cut off all on-leave semesters
    # at the beginning of the next program in the list. 

    for program, next_program in pairs(programs):
        if int(program['end']) > int(next_program['start']):
            program['end'] = next_program['start'] 
        for on_leave in program['on_leave']:
            if int(on_leave) > int(program['end']):
                program['on_leave'].remove(on_leave)
    
    # group the on-leave semesters
    for program in programs:
        on_leave = []
        if len(program['on_leave']) > 0:
            last_group = (program['on_leave'][0], program['on_leave'][0]) 
            last_group_pushed = False
            for semester in program['on_leave']:
                if semester in last_group or int(semester) > int(program['end']):
                    continue
                if semester == lazy_next_semester(last_group[1]):
                    last_group = ( last_group[0], semester )
                    last_group_pushed = False
                else: 
                    on_leave.append(last_group)
                    last_group = (semester, semester) 
                    last_group_pushed = True
            if not last_group_pushed: 
                on_leave.append(last_group) 
        program['on_leave'] = on_leave 

    # does this program have admission records? 
    for program in programs:
        adm_appl_nbrs = guess_adm_appl_nbr(emplid, program['program_code'], program['start'], program['end'] )
        if len(adm_appl_nbrs) > 0:
            program['adm_appl_nbr'] = str(adm_appl_nbrs[0])
            program['admission_records'] = get_admission_records(emplid, program['adm_appl_nbr'])
        else:
            adm_appl_nbrs = guess_harder_at_adm_appl_nbr(emplid, program['program_code'], program['start'], program['end'] )
            if len(adm_appl_nbrs) > 0:
                program['adm_appl_nbr'] = str(adm_appl_nbrs[0])
                program['admission_records'] = get_admission_records(emplid, program['adm_appl_nbr'])
            else: 
                program['adm_appl_nbr'] = None 

    return programs 

def merge_leaves( programs ):
    """
    Given a list of programs, return a merged list of on-leaves
    [ 
        { 'start':'1111', 'end':'1131', 'on_leave':[ ('1131', '1134') ] ... }
        { 'start':'1134', 'end':'1141', 'on_leave':[ ('1134', '1141') ] ... }
    ]
    ==> 
    [ ('1131', '1141') ]
    """

    # create a master-list of leaves
    all_leaves = []
    for program in programs:
        for on_leave in program['on_leave']:
            all_leaves.append(on_leave)

    # merge on-leaves that border semesters
    ps = [x for x in pairs(all_leaves)]
    for leave, next_leave in ps: 
        if ( leave[1] == next_leave[0] or 
            leave[1] == lazy_next_semester(next_leave[0]) ): 
            all_leaves.remove(leave)
            all_leaves.remove(next_leave)
            all_leaves.append( (leave[0], next_leave[1] ) )

    all_leaves = sorted( all_leaves, key= lambda x : int(x[0]) )
    return all_leaves

#@cache_by_args
@SIMS_problem_handler
def get_student_programs(emplid):
    db = SIMSConn()
    query = """SELECT DISTINCT ACAD_PROG_PRIMARY, STRM, UNT_TAKEN_PRGRSS FROM PS_STDNT_CAR_TERM 
        WHERE EMPLID=%s
        """
    db.execute(query, (str(emplid),))
    return list(db)

#@cache_by_args
@SIMS_problem_handler
def get_on_leave_semesters(emplid):
    db = SIMSConn()
    query = """SELECT DISTINCT STRM, WITHDRAW_REASON FROM PS_STDNT_CAR_TERM 
        WHERE
        EMPLID = %s
        AND WITHDRAW_CODE != 'NWD' 
        AND WITHDRAW_REASON IN ('OL', 'MEDI', 'AP')
        AND ACAD_CAREER='GRAD'
        ORDER BY STRM """
    db.execute(query, (str(emplid),))
    return list(db)

#@cache_by_args
@SIMS_problem_handler
def get_end_of_degree(emplid, acad_prog, start_semester):
    """ 
        How did this acad_prog (e.g. "ESPHD") end? 
            DISC -> discontinued
            COMP -> completed
    """ 
    db = SIMSConn()
    query = """SELECT DISTINCT 
        PROG_ACTION, 
        PROG_REASON, 
        ACTION_DT
        FROM PS_ACAD_PROG PROG 
        WHERE 
            PROG_ACTION IN ('DISC', 'COMP')
            AND EMPLID=%s 
            AND ACAD_PROG=%s
            AND REQ_TERM >= %s
            AND PROG.EFFDT = ( SELECT MAX(TMP.EFFDT) 
                                FROM PS_ACAD_PROG TMP
                                WHERE TMP.EMPLID = PROG.EMPLID
                                AND PROG.PROG_ACTION = TMP.PROG_ACTION
                                AND PROG.ACAD_PROG = TMP.ACAD_PROG
                                AND TMP.EFFDT <= GETDATE() )
            AND PROG.EFFSEQ = ( SELECT MAX(TMP2.EFFSEQ)
                                FROM PS_ACAD_PROG TMP2
                                WHERE TMP2.EMPLID = PROG.EMPLID
                                AND PROG.PROG_ACTION = TMP2.PROG_ACTION
                                AND PROG.ACAD_PROG = TMP2.ACAD_PROG
                                AND PROG_ACTION IN ('DISC', 'COMP')
                                AND TMP2.EFFDT = PROG.EFFDT )
        ORDER BY ACTION_DT
        OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY
            """ 
    db.execute(query, (str(emplid),str(acad_prog),str(start_semester)))
    result = [(x[0], x[1], x[2]) for x in list(db)]
    if len(result) > 1:
        print("\t Recoverable Error: More than one end of degree ", result)
        return result[0]
    elif len(result) > 0:
        return result[0]
    else:
        return None

#@cache_by_args
@SIMS_problem_handler
def guess_adm_appl_nbr(emplid, acad_prog, start_semester, end_semester):
    """
    Given an acad_prog, find any adm_appl_nbr records between start_semester
    and end_semester that didn't result in a rejection
    """
    db = SIMSConn()
    query = """
        SELECT DISTINCT 
            PROG.ADM_APPL_NBR 
        FROM PS_ADM_APPL_PROG PROG
        LEFT JOIN PS_ADM_APPL_DATA DATA
            ON PROG.ADM_APPL_NBR = DATA.ADM_APPL_NBR
        WHERE 
            PROG.EMPLID = %s
                AND PROG.PROG_STATUS NOT IN ('DC') 
            AND ( DATA.APPL_FEE_STATUS IN ('REC', 'WVD')
                  OR DATA.ADM_APPL_CTR IN ('GRAW') )
            AND PROG.ACAD_PROG = %s
            AND PROG.PROG_ACTION IN ('ADMT', 'ACTV', 'COND', 'MATR') 
            AND PROG.ADMIT_TERM >= %s
            AND PROG.ADMIT_TERM <= %s
        """
    db.execute(query, (str(emplid), str(acad_prog), str(start_semester), str(end_semester)))
    return [x[0] for x in list(db)]

@SIMS_problem_handler
def guess_harder_at_adm_appl_nbr( emplid, acad_prog, start_semester, end_semester ):
    """
    Okay, so the first guess didn't turn up anything. Let's try being a little bit looser
    about our criteria - 
    a wider time slot
     AND 
    any adm_appl record that didn't end in rejection.
    """
    year_before_start_semester = offset_semester_string(start_semester, -3)
    db = SIMSConn()
    query = """
        SELECT DISTINCT 
            PROG.ADM_APPL_NBR 
        FROM PS_ADM_APPL_PROG PROG
        LEFT JOIN PS_ADM_APPL_DATA DATA
            ON PROG.ADM_APPL_NBR = DATA.ADM_APPL_NBR
        WHERE 
            PROG.EMPLID = %s
                AND PROG.PROG_STATUS NOT IN ('DC') 
            AND ( DATA.APPL_FEE_STATUS IN ('REC', 'WVD')
                  OR DATA.ADM_APPL_CTR IN ('GRAW') )
            AND PROG.ACAD_PROG = %s
            AND PROG.ADMIT_TERM >= %s
            AND PROG.ADMIT_TERM <= %s
        """
    db.execute(query, (str(emplid), str(acad_prog), str(year_before_start_semester), str(end_semester)))
    adm_appls = [x[0] for x in list(db)]

    query2 = """
        SELECT DISTINCT 
            PROG.ADM_APPL_NBR 
        FROM PS_ADM_APPL_PROG PROG
        LEFT JOIN PS_ADM_APPL_DATA DATA
            ON PROG.ADM_APPL_NBR = DATA.ADM_APPL_NBR
        WHERE 
            PROG.EMPLID = %s
                AND PROG.PROG_STATUS NOT IN ('DC') 
            AND ( DATA.APPL_FEE_STATUS IN ('REC', 'WVD')
                  OR DATA.ADM_APPL_CTR IN ('GRAW') )
            AND PROG.ACAD_PROG = %s
            AND PROG.PROG_ACTION IN ('DDEF', 'DEFR', 'DENY', 'WAIT') 
    """

    db.execute(query2, (str(emplid), str(acad_prog)))
    rejected = [x[0] for x in list(db)]
    return [x for x in adm_appls if x not in rejected]

@SIMS_problem_handler
def get_adm_appl_nbrs( emplid ):
    """
    Given an acad_prog, find all adm_appl_nbr s
    """
    db = SIMSConn()
    query = """
        SELECT DISTINCT 
            PROG.ADM_APPL_NBR,
            PROG.ACAD_PROG 
        FROM PS_ADM_APPL_PROG PROG
        LEFT JOIN PS_ADM_APPL_DATA DATA
            ON PROG.ADM_APPL_NBR = DATA.ADM_APPL_NBR
        WHERE 
            PROG.EMPLID = %s
                AND PROG.PROG_STATUS NOT IN ('DC') 
            AND ( DATA.APPL_FEE_STATUS IN ('REC', 'WVD')
                  OR DATA.ADM_APPL_CTR IN ('GRAW') )
        """
    db.execute(query, (str(emplid),))
    return list(db)
    return [str(x[0]) for x in list(db)]

def find_or_generate_person(emplid):
    # return a Person object, even if you have to make it yourself
    # throws IntegrityError, SIMSProblem
    try:
        p = Person.objects.get(emplid=emplid)
        return p
    except Person.DoesNotExist:
        p = add_person( emplid )
        return p

#@cache_by_args
@SIMS_problem_handler
def get_admission_records( emplid, adm_appl_nbr ):
    """
    The ps_adm_appl_prog table holds records relevant to a grad student's
    application to a program. 
    """
    db = SIMSConn()
    query = """
        SELECT DISTINCT 
            PROG.PROG_ACTION, 
            PROG.ACTION_DT, 
            PROG.ADMIT_TERM
        FROM PS_ADM_APPL_PROG PROG
        WHERE 
            PROG.EMPLID = %s
            AND PROG.ADM_APPL_NBR = %s
            AND PROG_ACTION IN ('APPL', 'ADMT', 'COND', 'DENY', 'MATR', 'WAPP', 'WADM') 
        ORDER BY ACTION_DT, PROG_ACTION
        """
    db.execute(query, (str(emplid), str(adm_appl_nbr)))
    return list(db)

@SIMS_problem_handler
def get_supervisory_committee(emplid, min_date=None, max_date=None):
    if not min_date:
        # I refuse to believe that the world existed before I was born
        min_date = datetime.date(1986,9,1)
    if not max_date:
        max_date = datetime.date.today()
    db = SIMSConn()
    query = """
        SELECT DISTINCT 
            ROLE.DESCR, 
            MEM.EMPLID,
            COM.EFFDT
        FROM 
            PS_SFU_STDNT_CMTTE ST, 
            PS_COMMITTEE COM, 
            PS_COMMITTEE_MEMBR MEM, 
            PS_COMMITTEE_TBL COMTBL, 
            PS_COMMIT_ROLE_TBL ROLE
        WHERE 
            COM.INSTITUTION=ST.INSTITUTION 
            AND COM.COMMITTEE_ID=ST.COMMITTEE_ID
            AND MEM.INSTITUTION=COM.INSTITUTION 
            AND MEM.COMMITTEE_ID=COM.COMMITTEE_ID 
            AND MEM.EFFDT=COM.EFFDT
            AND COM.COMMITTEE_TYPE=COMTBL.COMMITTEE_TYPE 
            AND COMTBL.EFF_STATUS='A'
            AND ROLE.COMMITTEE_ROLE=MEM.COMMITTEE_ROLE 
            AND ROLE.COMMITTEE_TYPE=COM.COMMITTEE_TYPE
            AND ST.EMPLID=%s
            AND COM.EFFDT = ( SELECT MAX(TMP.EFFDT)
                                FROM PS_COMMITTEE TMP
                                WHERE TMP.COMMITTEE_ID = COM.COMMITTEE_ID
                                AND EFFDT > %s
                                AND EFFDT < %s
                                AND TMP.COMMITTEE_TYPE = COM.COMMITTEE_TYPE )
        """
    db.execute(query, (str(emplid), min_date, max_date))
    return list(db)

#@cache_by_args
@SIMS_problem_handler
def holds_resident_visa( emplid ):
    db = SIMSConn()
    db.execute("""
        SELECT *
        FROM PS_VISA_PERMIT_TBL TBL
        INNER JOIN PS_VISA_PMT_DATA DATA
            ON TBL.VISA_PERMIT_TYPE = DATA.VISA_PERMIT_TYPE
        WHERE
            DATA.EFFDT = ( SELECT MAX(TMP.EFFDT) 
                                FROM PS_VISA_PMT_DATA TMP
                                WHERE TMP.EMPLID = DATA.EMPLID
                                    AND TMP.EFFDT <= GETDATE() )
            AND DATA.EMPLID = %s
            AND VISA_PERMIT_CLASS = 'R'
        """, (emplid,) )
    # If there's at least one record with Permit Class TYPE R!, they are a resident
    for result in db:
        return True
    return False

#@cache_by_args
@SIMS_problem_handler
def get_mother_tongue( emplid ):
    db = SIMSConn()
    db.execute("""
        SELECT ATBL.DESCR
          FROM PS_ACCOMPLISHMENTS A,
               PS_ACCOMP_TBL     ATBL
         WHERE A.EMPLID=%s
           AND A.NATIVE_LANGUAGE='Y'
           AND A.ACCOMPLISHMENT=ATBL.ACCOMPLISHMENT
           AND ATBL.ACCOMP_CATEGORY='LNG'
        """, (emplid,) )
    for result in db:
        return str(result[0])
    return "Unknown"

#@cache_by_args
@SIMS_problem_handler
def get_passport_issued_by( emplid ):
    db = SIMSConn()
    db.execute("""
        SELECT COU.DESCR 
        FROM PS_COUNTRY_TBL COU
        INNER JOIN PS_CITIZENSHIP CIT 
            ON CIT.COUNTRY = COU.COUNTRY
        WHERE CIT.EMPLID = %s
        """, (emplid,) )
    for result in db:
        return str(result[0])
    return "Unknown"


@SIMS_problem_handler
def csrpt_update():
    """
    Report about when it looks like the reporting database was last updated
    """
    import pyodbc
    data = []
    db = SIMSConn()
    this_sem = Semester.current()

    try:
        db.execute("""
            SELECT SFU_CLONE_DTTM FROM PS_SFU_CLONE_INFO
            """, ())
        row = db.fetchone()
        if row:
            data.append(('ps_sfu_clone_info.sfu_clone_dttm', row[0]))
    except (SIMSProblem, pyodbc.ProgrammingError) as e:
        data.append(('ps_sfu_clone_info.sfu_clone_dttm', 'Unable to query: ' + str(e)))

    db.execute("""
        SELECT MAX(ENRL_ADD_DT), MAX(STATUS_DT), MAX(GRADING_BASIS_DT) FROM PS_STDNT_ENRL WHERE STRM IN (%s, %s)
        """, (this_sem.name, this_sem.offset_name(1)))
    row = db.fetchone()
    if row:
        data.append(('max(enrl_add_dt)', row[0]))
        data.append(('max(status_dt)', row[1]))
        data.append(('max(grading_basis_dt)', row[2]))

    db.execute("""
        SELECT MAX(SCC_ROW_ADD_DTTM) FROM PS_ACAD_PLAN
        """, ())
    row = db.fetchone()
    if row:
        data.append(('recent ps_acad_plan', row[0]))

    return data


##############################################################################3
# Course outlines API functions
# as documented here: http://www.sfu.ca/outlines/help/api.html

OUTLINES_BASE_URL = 'http://www.sfu.ca/bin/wcm/course-outlines'
OUTLINES_FRONTEND_BASE = 'http://www.sfu.ca/outlines.html'
def outlines_api_url(offering):
    """
    The URL for info in the API.
    """
    from urllib.parse import quote_plus as q

    args = {
        'year': q(str(int(offering.semester.name[0:3]) + 1900)),
        'term': q(Semester.label_lookup[offering.semester.name[3]].lower()),
        'dept': q(offering.subject.lower()),
        'number': q(offering.number.lower()),
        'section': q(offering.section.lower()),
    }
    qs = 'year={year}&term={term}&dept={dept}&number={number}&section={section}'.format(**args)
    return OUTLINES_BASE_URL + '?' + qs


def outlines_data_json(offering):
    url = outlines_api_url(offering)
    url_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        req = url_opener.open(url, timeout=30)
        jsondata = req.read()
        data = json.loads(jsondata.decode('utf8'))
    except ValueError:
        data = {'internal_error': 'could not decode JSON'}
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, socket.error):
        data = {'internal_error': 'could not retrieve outline data from API'}

    if 'info' in data and 'outlinePath' in data['info']:
        data['outlineurl'] = OUTLINES_FRONTEND_BASE + '?' + data['info']['outlinePath']

    return json.dumps(data, indent=1)



##############################################################################
# Emplid -> Userid APIs

EMPLID_SECRET = settings.EMPLID_API_SECRET
EMPLID_BASE_URL = 'https://rest.its.sfu.ca/cgi-bin/WebObjects/AOBRestServer.woa/rest/datastore2/global.json?'
USERID_BASE_URL = 'https://rest.its.sfu.ca/cgi-bin/WebObjects/AOBRestServer.woa/rest/amaint/username/username.json?'

def userid_to_emplid(userid):
    """
    Fetch emplid from ITS API for userid -> emplid mapping.

    Admin contact for the API is George Lee in the Learning & Community Platforms Group
    """
    qs = urllib.parse.urlencode({'art': EMPLID_SECRET, 'username': userid})
    url = EMPLID_BASE_URL + qs
    url_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        req = url_opener.open(url, timeout=30)
        jsondata = req.read().decode('utf8')
        data = json.loads(jsondata)
    except ValueError:
        # can't decode JSON
        return None
    except (urllib.error.HTTPError, urllib.error.URLError, http.client.HTTPException, socket.timeout, socket.error):
        # network problem, or 404 (if userid doesn't exist)
        return None

    if 'sfuid' not in data:
        return None

    return data['sfuid']

def emplid_to_userid(emplid):
    """
    Fetch userid from ITS API for emplid -> userid mapping.

    Admin contact for the API is George Lee in the Learning & Community Platforms Group
    """
    qs = urllib.parse.urlencode({'art': EMPLID_SECRET, 'sfuid': str(emplid)})
    url = USERID_BASE_URL + qs
    url_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        req = url_opener.open(url, timeout=30)
        jsondata = req.read().decode('utf8')
        data = json.loads(jsondata)
    except ValueError:
        # can't decode JSON
        return None
    except (urllib.error.HTTPError, urllib.error.URLError, http.client.HTTPException):
        # network problem, or 404 (if userid doesn't exist)
        return None

    if 'username' not in data:
        raise ValueError("No 'username' returned in response.")

    userids = data['username']
    return userids.split(',')[0].strip()


def ensure_person_from_userid(userid):
    """
    Make sure the Person object for this userid exists.
    """
    p = Person.objects.filter(userid=userid)
    if p:
        # already have them: done.
        return p[0]

    # look up their emplid
    emplid = userid_to_emplid(userid)
    if not emplid:
        # can't find emplid: maybe a role account? Maybe out-of-sync databases? Fail quietly.
        return None

    p = Person.objects.filter(emplid=emplid)
    if p:
        # found the emplid: record the userid and return.
        p = p[0]
        p.userid = userid
        p.save()
        return p

    # we've never heard of them, but the University has.
    return build_person(emplid, userid)


def build_person(emplid, userid=None):
    """
    Build a Person object for this newly-discovered person
    """
    p = Person(emplid=emplid, userid=userid)
    return import_person(p)


def import_person(p, commit=True, grad_data=False):
    """
    Import SIMS (+ userid) information about this Person. Return the Person or None if they can't be found.
    """
    last_name, first_name, middle_name, pref_first_name, title = get_names(p.emplid)
    if last_name is None:
        # no name = no such person
        return None

    userid = emplid_to_userid(p.emplid)
    #if userid and len(userid) > 8:
    #    raise ValueError('userid too long', "We have a userid >8 characters: %r" % (userid,))

    p.last_name = last_name
    p.first_name = first_name
    p.middle_name = middle_name
    p.pref_first_name = pref_first_name
    p.title = title
    p.config['lastimport'] = int(time.time())

    # don't deactivate userids that have been deactivated by the University
    if userid:
        ## but freak out if a userid changes
        if p.userid and p.userid != userid:
            #raise ValueError, "Somebody's userid changed? %s became %s." % (p.userid, userid)
            mail_admins('userid change', "Somebody's userid changed: %s became %s." % (p.userid, userid))
        p.userid = userid

    if grad_data:
        data = grad_student_info(p.emplid)
        p.config.update(data)

        # if we tried to update but it's gone: don't keep old version
        for f in GRADFIELDS:
            if f not in data and f in p.config:
                del p.config[f]

    if commit:
        p.save()
        # this might now throw an IntegrityError if the new userid is re-used for another person,
        # but that's *never* supposed to happen, just like changing a userid. See commented-out code
        # from importer._person_save if it starts happening.

    return p





