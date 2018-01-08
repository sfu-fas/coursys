from coredata.models import Person, Semester, SemesterWeek, CourseOffering
from django.conf import settings
from django.core.mail import mail_admins
import django.db.transaction
from django.core.cache import cache
from django.utils.html import conditional_escape as e
from featureflags.flags import feature_disabled
import re, hashlib, datetime, string, urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse, http.client, time, json
import socket

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

class SIMSConn(DBConn):
    """
    Singleton object representing SIMS DB connection
    """
    sims_user = settings.SIMS_USER
    sims_passwd = settings.SIMS_PASSWORD
    sims_db = settings.SIMS_DB_NAME
    schema = settings.SIMS_DB_SCHEMA
    
    DatabaseError = None
    DB2Error = None

    def get_connection(self):
        if settings.DISABLE_REPORTING_DB:
            raise SIMSProblem("Reporting database access has been disabled in this deployment.")
        elif feature_disabled('sims'):
            raise SIMSProblem("Reporting database access has been temporarily disabled due to server maintenance or load.")

        try:
            import DB2
        except ImportError:
            raise SIMSProblem("could not import DB2 module")
        SIMSConn.DatabaseError = DB2.DatabaseError
        SIMSConn.DB2Error = DB2.Error
        try:
            dbconn = DB2.connect(dsn=self.sims_db, uid=self.sims_user, pwd=self.sims_passwd)
        except DB2._db2.DatabaseError:
            raise SIMSProblem("Could not communicate with reporting database.")
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
        a = str(a).encode('utf8')
        a = a.replace("\\", "\\\\")
        a = a.replace("'", "\\'")
        a = a.replace('"', '\\"')
        a = a.replace("\r", "\\r")
        a = a.replace("\n", "\\n")
        a = a.replace("\x00", "\\\x00")
        a = a.replace("\x1a", "\\\x1a")
        return "'"+a+"'"

    def prep_value(self, v):
        """
        get DB2 value into a useful format
        """
        if isinstance(v, str):
            # First try decoding it as UTF-8.  If that fails, decode it with Windows-1250 encoding, as that
            # seems to be the other case we get.
            try:
                return v.strip().decode('utf8')
            except UnicodeDecodeError:
                return v.strip().decode('windows-1250')
        else:
            return v


class SIMSProblem(Exception):
    """
    Class used to pass back problems with the SIMS connection.
    """
    pass

def SIMS_problem_handler(func):
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

def _args_to_key(args, kwargs):
    "Hash arguments to get a cache key"
    h = hashlib.new('md5')
    h.update(str(args))
    h.update(str(kwargs))
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
    db.execute("SELECT e_addr_type, email_addr, pref_email_flag FROM ps_email_addresses c WHERE e_addr_type='CAMP' and emplid=%s", (str(emplid),))
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
    db.execute("SELECT emplid, last_name, first_name, middle_name FROM ps_personal_data WHERE emplid=%s",
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
    db.execute("SELECT email_addr FROM ps_email_addresses WHERE emplid=%s AND e_addr_type='WORK'",
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
    
    db.execute("SELECT name_type, name_prefix, last_name, first_name, middle_name FROM ps_names WHERE "
               "emplid=%s AND eff_status='A' AND name_type IN ('PRI','PRF') "
               "ORDER BY effdt", (str(emplid),))
    # order by effdt to leave the latest in the dictionary at end
    for name_type, prefix, last, first, middle in db:
        if name_type == 'PRI':
            last_name = last
            first_name = first
            middle_name = middle
            title = prefix
        elif name_type == 'PRF':
            pref_first_name = first

    # ensure we have a pref_first_name of some kind
    #if not pref_first_name:
    #    pref_first_name = first_name
    
    return last_name, first_name, middle_name, pref_first_name, title


GRADFIELDS = ['ccredits', 'citizen', 'gpa', 'gender', 'visa']
@cache_by_args
@SIMS_problem_handler
def grad_student_info(emplid):
    "The info we want in Person.config for all GradStudents"
    return more_personal_info(emplid, needed=GRADFIELDS)


PLAN_QUERY = string.Template("""
            SELECT prog.emplid, plantbl.acad_plan, plantbl.descr, plantbl.trnscr_descr
            FROM ps_acad_prog prog, ps_acad_plan plan, ps_acad_plan_tbl AS plantbl
            WHERE prog.emplid=plan.emplid AND prog.acad_career=plan.acad_career AND prog.stdnt_car_nbr=plan.stdnt_car_nbr AND prog.effdt=plan.effdt AND prog.effseq=plan.effseq
              AND plantbl.acad_plan=plan.acad_plan
              AND prog.effdt=(SELECT MAX(effdt) FROM ps_acad_prog WHERE emplid=prog.emplid AND acad_career=prog.acad_career AND stdnt_car_nbr=prog.stdnt_car_nbr AND effdt <= current date)
              AND prog.effseq=(SELECT MAX(effseq) FROM ps_acad_prog WHERE emplid=prog.emplid AND acad_career=prog.acad_career AND stdnt_car_nbr=prog.stdnt_car_nbr AND effdt=prog.effdt)
              AND plantbl.effdt=(SELECT MAX(effdt) FROM ps_acad_plan_tbl WHERE acad_plan=plantbl.acad_plan AND eff_status='A' and effdt<=current date)
              AND prog.prog_status='AC' AND plantbl.eff_status='A'
              AND $where
            ORDER BY prog.emplid, plan.plan_sequence""")

SUBPLAN_QUERY = string.Template("""
            SELECT prog.emplid, plantbl.acad_sub_plan, plantbl.descr, plantbl.trnscr_descr
            FROM ps_acad_prog prog, ps_acad_subplan plan, ps_acad_subpln_tbl AS plantbl
            WHERE prog.emplid=plan.emplid AND prog.stdnt_car_nbr=plan.stdnt_car_nbr AND prog.effdt=plan.effdt AND prog.effseq=plan.effseq
              AND plantbl.acad_plan=plan.acad_plan AND plantbl.acad_sub_plan=plan.acad_sub_plan
              AND prog.effdt=(SELECT MAX(effdt) FROM ps_acad_prog WHERE emplid=prog.emplid AND acad_career=prog.acad_career AND stdnt_car_nbr=prog.stdnt_car_nbr AND effdt <= current date)
              AND prog.effseq=(SELECT MAX(effseq) FROM ps_acad_prog WHERE emplid=prog.emplid AND acad_career=prog.acad_career AND stdnt_car_nbr=prog.stdnt_car_nbr AND effdt=prog.effdt)
              AND plantbl.effdt=(SELECT MAX(effdt) FROM ps_acad_plan_tbl WHERE acad_plan=plantbl.acad_plan AND eff_status='A' and effdt<=current date)
              AND prog.prog_status='AC' AND plantbl.eff_status='A'
              AND $where
            ORDER BY prog.emplid""")

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
        db.execute('SELECT phone_type, country_code, phone, extension, pref_phone_flag FROM ps_personal_phone WHERE emplid=%s', (str(emplid),))
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
        db.execute("SELECT address_type, effdt, eff_status, c.descrshort, address1, address2, address3, address4, city, state, postal FROM ps_addresses a, ps_country_tbl c WHERE emplid=%s AND eff_status='A' AND a.country=c.country ORDER BY effdt ASC", (str(emplid),))
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
        db.execute("SELECT c.descrshort FROM ps_citizenship cit, ps_country_tbl c WHERE emplid=%s AND cit.country=c.country", (str(emplid),))
        #if 'citizen' in p.config:
        #    del p.config['citizen']
        for country, in db:
            data['citizen'] = country

    # get Canadian visa status
    if (needed == ALLFIELDS or 'visa' in needed) and 'visa' not in exclude:
        # sorting by effdt to get the latest in the dictionary
        db.execute("SELECT t.descrshort FROM ps_visa_pmt_data v, ps_visa_permit_tbl t WHERE emplid=%s AND v.visa_permit_type=t.visa_permit_type AND v.country=t.country AND v.country='CAN' AND v.visa_wrkpmt_status='A' AND t.eff_status='A' ORDER BY v.effdt ASC", (str(emplid),))
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
        db.execute('SELECT sex FROM ps_personal_data WHERE emplid=%s', (str(emplid),))
        #if 'gender' in p.config:
        #    del p.config['gender']
        for sex, in db:
            if sex:
                data['gender'] = sex # 'M', 'F', 'U'    
    
    # academic programs
    if (needed == ALLFIELDS or 'programs' in needed) and 'programs' not in exclude:
        programs = []
        data['programs'] = programs
        db.execute(PLAN_QUERY.substitute({'where': 'prog.emplid=%s'}), (str(emplid),))
        #  AND apt.trnscr_print_fl='Y'
        for emplid, acad_plan, descr, transcript in db:
            label = transcript or descr
            prog = "%s (%s)" % (label, acad_plan)
            programs.append(prog)

        # also add academic subplans
        db.execute(SUBPLAN_QUERY.substitute({'where': 'prog.emplid=%s'}), (str(emplid),))
        for emplid, subplan, descr, transcript in db:
            label = transcript or descr
            prog = "%s (%s subplan)" % (label, subplan)
            programs.append(prog)



    # GPA and credit count
    if (needed == ALLFIELDS or 'gpa' in needed or 'ccredits' in needed) and 'ccredits' not in exclude:
        db.execute('SELECT cum_gpa, tot_cumulative FROM ps_stdnt_car_term WHERE emplid=%s ORDER BY strm DESC FETCH FIRST 1 ROWS ONLY', (str(emplid),))
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
        eff_where = "AND effdt<=%s" % (db.escape_arg(effdt.isoformat()))

    db.execute("""
        SELECT descr, ssr_component, course_title_long, descrlong
        FROM ps_crse_catalog
        WHERE eff_status='A' AND crse_id=%s """ + eff_where + """
        ORDER BY effdt DESC FETCH FIRST 1 ROWS ONLY""", (crse_id,))
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
    offering_query = "SELECT o.subject, o.catalog_nbr, c.descr FROM ps_crse_offer o, ps_crse_catalog c WHERE o.crse_id=c.crse_id AND o.crse_id=%s ORDER BY o.effdt DESC, c.effdt DESC FETCH FIRST 1 ROWS ONLY"
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
    ext_org_query = "SELECT e.descr FROM ps_ext_org_tbl e WHERE e.eff_status='A' AND e.ext_org_id=%s ORDER BY effdt DESC FETCH FIRST 1 ROWS ONLY"
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
    
    db.execute("""SELECT r.rqmnt_designtn, r.descrshort FROM ps_rqmnt_desig_tbl r
        WHERE r.EFFDT=(SELECT MAX(effdt) FROM ps_rqmnt_desig_tbl
                       WHERE rqmnt_designtn=r.rqmnt_designtn AND r.effdt<=current date AND eff_status='A')
            AND r.eff_status='A'""", ())
    return dict(db)
    
@cache_by_args
def get_semester_names():
    """
    Get and cache semester names (to avoid joining yet another table).
    """
    db = SIMSConn()
    
    db.execute("SELECT t.strm, t.descr FROM ps_term_tbl t", ())
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
    crse_join = "t.emplid=s.emplid AND t.acad_career=s.acad_career AND t.institution=s.institution AND t.model_nbr=s.model_nbr"
    
    # transfers
    transfer_query = "SELECT t.crse_id, t.crse_grade_off, t.unt_trnsfr, t.repeat_code, t.articulation_term, " \
                     " t.rqmnt_designtn, s.ext_org_id, s.src_org_name " \
                     "FROM ps_trns_crse_dtl t, ps_trns_crse_sch s " \
                     "WHERE " + crse_join + " AND t.emplid=%s"
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
    term_query = "SELECT t.strm, t.acad_career, t.tot_passd_prgrss, t.cur_gpa, t.cum_gpa, s.acad_stndng_actn, g.ls_gpa " \
                 "FROM ps_stdnt_car_term t " \
                 " LEFT JOIN ps_acad_stdng_actn s ON t.emplid=s.emplid AND t.strm=s.strm " \
                 " LEFT JOIN ps_stdnt_spcl_gpa g ON t.emplid=g.emplid AND t.strm=g.strm " \
                 "WHERE t.emplid=%s AND (g.gpa_type='UGPA' OR g.gpa_type IS NULL) " \
                 "ORDER BY t.strm, s.effdt DESC, s.effseq DESC"
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
    enrl_query = "SELECT e.strm, e.class_nbr, e.unt_taken, " \
                 "e.repeat_code, e.crse_grade_off, e.rqmnt_designtn, " \
                 "c.subject, c.catalog_nbr, c.descr " \
                 "FROM ps_stdnt_enrl e, ps_class_tbl c " \
                 "WHERE e.class_nbr=c.class_nbr AND e.strm=c.strm AND e.emplid=%s " \
                 "AND c.class_type='E' AND e.stdnt_enrl_status='E' " \
                 "ORDER BY e.strm, c.subject, c.catalog_nbr"
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
    transfers = "WITH crse_offer AS (select crse_id, CRSE_OFFER_NBR, subject, catalog_nbr from dbcsown.ps_crse_offer "\
                "A where effdt=(SELECT MAX(effdt) FROM dbcsown.ps_crse_offer WHERE crse_id=A.crse_id)), ext_org_tbl AS"\
                "(select ext_org_id, descr50 from dbcsown.ps_ext_org_tbl A where effdt=(SELECT MAX(effdt) FROM"\
                " dbcsown.ps_ext_org_tbl WHERE ext_org_id=A.ext_org_id))"\
                "select tcd.emplid, eot.descr50, ec.SCHOOL_SUBJECT, ec.SCHOOL_CRSE_NBR, tcd.trnsfr_eqvlncy_grp, "\
                "tcd.trnsfr_stat, co.subject, co.catalog_nbr, tcd.CRSE_GRADE_INPUT as tcd_grade_input, "\
                "tcd.crse_grade_off as tcd_grade_off,ec.CRSE_GRADE_INPUT as ec_grade_input, ec.crse_grade_off "\
                "as ec_grade_off, tcd.UNT_TRNSFR "\
                "from dbcsown.ps_trns_crse_dtl tcd inner join dbcsown.ps_trns_crse_sch tcs on tcs.emplid=tcd.emplid "\
                "and tcd.acad_career=tcs.acad_career and tcd.institution=tcs.institution and "\
                "tcd.model_nbr=tcs.model_nbr left outer join dbcsown.ps_ext_course ec on ec.emplid=tcd.emplid and "\
                "ec.ext_course_nbr=tcd.ext_course_nbr and ec.ext_org_id=tcs.ext_org_id left outer join ext_org_tbl "\
                "eot on tcd.TRNSFR_SRC_ID = eot.ext_org_id left outer join crse_offer co on tcd.crse_id = co.crse_id "\
                "and tcd.CRSE_OFFER_NBR = co.CRSE_OFFER_NBR where tcd.trnsfr_stat='P' and tcs.model_status='P' "\
                "and tcd.emplid=%s order by tcd.model_nbr, tcd.TRNSFR_EQVLNCY_GRP, tcd.TRNSFR_EQVLNCY_SEQ"
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
    courses = "SELECT e.strm, c.subject, c.catalog_nbr, c.descr, e.crse_grade_off, e.unt_taken "\
                 "FROM ps_stdnt_enrl e, ps_class_tbl c "\
                 "WHERE e.class_nbr=c.class_nbr AND e.strm=c.strm AND e.emplid=%s "\
                 "AND c.class_type='E' AND e.stdnt_enrl_status='E' "\
                 "ORDER BY e.strm, c.subject, c.catalog_nbr"
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
    last_prog_plan = "(SELECT ap.emplid, max(ap.effdt) as effdtprog, max(ap2.effdt) as effdt " \
                     "FROM ps_acad_plan ap, ps_acad_plan ap2, ps_stdnt_car_term ct "\
                     "WHERE ap.emplid=ct.emplid and ap.emplid=ap2.emplid and ct.strm=%s and ap.acad_plan=%s " \
                     "and ct.stdnt_car_nbr=ap.stdnt_car_nbr GROUP BY ap.emplid)"

    # select those whose most recent program is in this acad_plan
    db.execute("SELECT count(*) FROM " + last_prog_plan + " WHERE effdtprog=effdt", (strm, acad_plan))
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
    db.execute("SELECT strm, term_begin_dt, term_end_dt FROM ps_term_tbl WHERE strm=%s", (strm,))
    row = db.fetchone()
    if row is None:
        raise ValueError("Not Found: %r" % strm)
    strm, st, en = row
    
    # create Semester object
    st = datetime.datetime.strptime(st, "%Y-%m-%d").date()
    en = datetime.datetime.strptime(en, "%Y-%m-%d").date()
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
    query = "SELECT e.strm, c.subject, c.catalog_nbr, c.class_section, c.class_nbr, " \
                 "e.unt_taken, e.crse_grade_off, e.grade_points " \
                 "FROM ps_stdnt_enrl e, ps_class_tbl c " \
                 "WHERE e.class_nbr=c.class_nbr AND e.strm=c.strm AND e.emplid=%s " \
                 "AND c.class_type='E' AND e.stdnt_enrl_status='E' AND e.acad_career='GRAD' " \
                 "ORDER BY e.strm, c.subject, c.catalog_nbr"
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
    query = "SELECT t.strm, t.cur_gpa, t.cum_gpa " \
                 "FROM ps_stdnt_car_term t " \
                 "WHERE t.emplid=%s AND t.acad_career='GRAD'"
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
    query = """SELECT DISTINCT acad_prog_primary, strm, unt_taken_prgrss FROM ps_stdnt_car_term 
        WHERE emplid=%s
        """
    db.execute(query, (str(emplid),))
    return list(db)

#@cache_by_args
@SIMS_problem_handler
def get_on_leave_semesters(emplid):
    db = SIMSConn()
    query = """SELECT DISTINCT strm, withdraw_reason FROM ps_stdnt_car_term 
        WHERE
        emplid = %s
        AND withdraw_code != 'NWD' 
        AND withdraw_reason IN ('OL', 'MEDI', 'AP')
        AND acad_career='GRAD'
        ORDER BY strm """
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
        prog_action, 
        prog_reason, 
        action_dt
        FROM ps_acad_prog prog 
        WHERE 
            prog_action in ('DISC', 'COMP')
            AND emplid=%s 
            AND acad_prog=%s
            AND req_term >= %s
            AND prog.effdt = ( SELECT MAX(tmp.effdt) 
                                FROM ps_acad_prog tmp
                                WHERE tmp.emplid = prog.emplid
                                AND prog.prog_action = tmp.prog_action
                                AND prog.acad_prog = tmp.acad_prog
                                AND tmp.effdt <= (SELECT current timestamp FROM sysibm.sysdummy1) )
            AND prog.effseq = ( SELECT MAX(tmp2.effseq)
                                FROM ps_acad_prog tmp2
                                WHERE tmp2.emplid = prog.emplid
                                AND prog.prog_action = tmp2.prog_action
                                AND prog.acad_prog = tmp2.acad_prog
                                AND prog_action in ('DISC', 'COMP')
                                AND tmp2.effdt = prog.effdt )
        ORDER BY action_dt
        FETCH FIRST 1 ROWS ONLY
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
def guess_adm_appl_nbr( emplid, acad_prog, start_semester, end_semester ):
    """
    Given an acad_prog, find any adm_appl_nbr records between start_semester
    and end_semester that didn't result in a rejection
    """
    db = SIMSConn()
    query = """
        SELECT DISTINCT 
            prog.adm_appl_nbr 
        FROM ps_adm_appl_prog prog
        LEFT JOIN ps_adm_appl_data data
            ON prog.adm_appl_nbr = data.adm_appl_nbr
        WHERE 
            prog.emplid = %s
                AND prog.prog_status NOT IN ('DC') 
            AND ( data.appl_fee_status in ('REC', 'WVD')
                  OR data.adm_appl_ctr in ('GRAW') )
            AND prog.acad_prog = %s
            AND prog.prog_action in ('ADMT', 'ACTV', 'COND', 'MATR') 
            AND prog.admit_term >= %s
            AND prog.admit_term <= %s
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
            prog.adm_appl_nbr 
        FROM ps_adm_appl_prog prog
        LEFT JOIN ps_adm_appl_data data
            ON prog.adm_appl_nbr = data.adm_appl_nbr
        WHERE 
            prog.emplid = %s
                AND prog.prog_status NOT IN ('DC') 
            AND ( data.appl_fee_status in ('REC', 'WVD')
                  OR data.adm_appl_ctr in ('GRAW') )
            AND prog.acad_prog = %s
            AND prog.admit_term >= %s
            AND prog.admit_term <= %s
        """
    db.execute(query, (str(emplid), str(acad_prog), str(year_before_start_semester), str(end_semester)))
    adm_appls = [x[0] for x in list(db)]

    query2 = """
        SELECT DISTINCT 
            prog.adm_appl_nbr 
        FROM ps_adm_appl_prog prog
        LEFT JOIN ps_adm_appl_data data
            ON prog.adm_appl_nbr = data.adm_appl_nbr
        WHERE 
            prog.emplid = %s
                AND prog.prog_status NOT IN ('DC') 
            AND ( data.appl_fee_status in ('REC', 'WVD')
                  OR data.adm_appl_ctr in ('GRAW') )
            AND prog.acad_prog = %s
            AND prog.prog_action in ('DDEF', 'DEFR', 'DENY', 'WAIT') 
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
            prog.adm_appl_nbr,
            prog.acad_prog 
        FROM ps_adm_appl_prog prog
        LEFT JOIN ps_adm_appl_data data
            ON prog.adm_appl_nbr = data.adm_appl_nbr
        WHERE 
            prog.emplid = %s
                AND prog.prog_status NOT IN ('DC') 
            AND ( data.appl_fee_status in ('REC', 'WVD')
                  OR data.adm_appl_ctr in ('GRAW') )
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
            prog.prog_action, 
            prog.action_dt, 
            prog.admit_term
        FROM ps_adm_appl_prog prog
        WHERE 
            prog.emplid = %s
            AND prog.adm_appl_nbr = %s
            AND prog_action IN ('APPL', 'ADMT', 'COND', 'DENY', 'MATR', 'WAPP', 'WADM') 
        ORDER BY action_dt, prog_action
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
            role.descr, 
            mem.emplid,
            com.effdt
        FROM 
            ps_stdnt_advr_hist st, 
            ps_committee com, 
            ps_committee_membr mem, 
            ps_committee_tbl comtbl, 
            ps_commit_role_tbl role
        WHERE 
            com.institution=st.institution 
            AND com.committee_id=st.committee_id
            AND mem.institution=com.institution 
            AND mem.committee_id=com.committee_id 
            AND mem.effdt=com.effdt
            AND com.committee_type=comtbl.committee_type 
            AND comtbl.eff_status='A'
            AND role.committee_role=mem.committee_role 
            AND role.committee_type=com.committee_type
            AND st.emplid=%s
            AND com.effdt = ( SELECT MAX(tmp.effdt)
                                FROM ps_committee tmp
                                WHERE tmp.committee_id = com.committee_id
                                AND effdt > DATE(%s)
                                AND effdt < DATE(%s)
                                AND tmp.committee_type = com.committee_type )
        """
    db.execute(query, (str(emplid), str(min_date), str(max_date) ))
    return list(db)

#@cache_by_args
@SIMS_problem_handler
def holds_resident_visa( emplid ):
    db = SIMSConn()
    db.execute("""
        SELECT *
        FROM ps_visa_permit_tbl tbl
        INNER JOIN ps_visa_pmt_data data
            ON tbl.visa_permit_type = data.visa_permit_type
        WHERE
            data.effdt = ( SELECT MAX(tmp.effdt) 
                                FROM ps_visa_pmt_data tmp
                                WHERE tmp.emplid = data.emplid
                                    AND tmp.effdt <= (SELECT current timestamp FROM sysibm.sysdummy1) )
            AND data.emplid = %s
            AND visa_permit_class = 'R'
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
        SELECT atbl.descr
          FROM ps_accomplishments a,
               ps_accomp_tbl     atbl
         WHERE a.emplid=%s
           AND a.native_language='Y'
           AND a.accomplishment=atbl.accomplishment
           AND atbl.accomp_category='LNG'
        """, (emplid,) )
    for result in db:
        return str(result[0])
    return "Unknown"

#@cache_by_args
@SIMS_problem_handler
def get_passport_issued_by( emplid ):
    db = SIMSConn()
    db.execute("""
        SELECT cou.descr 
        FROM ps_country_tbl cou
        INNER JOIN ps_citizenship cit 
            ON cit.country = cou.country
        WHERE cit.emplid = %s
        """, (emplid,) )
    for result in db:
        return str(result[0])
    return "Unknown"


@SIMS_problem_handler
def csrpt_update():
    """
    Report about when it looks like the reporting database was last updated
    """
    data = []
    db = SIMSConn()
    this_sem = Semester.current()

    db.execute("""
        SELECT sfu_clone_dttm FROM ps_sfu_clone_info
        """, ())
    row = db.fetchone()
    data.append(('ps_sfu_clone_info.sfu_clone_dttm', row[0]))

    db.execute("""
        SELECT max(enrl_add_dt), max(status_dt), max(grading_basis_dt) FROm ps_stdnt_enrl WHERE strm IN (%s, %s)
        """, (this_sem.name, this_sem.offset_name(1)))
    row = db.fetchone()
    data.append(('max(enrl_add_dt)', row[0]))
    data.append(('max(status_dt)', row[1]))
    data.append(('max(grading_basis_dt)', row[2]))

    db.execute("""
        SELECT max(scc_row_add_dttm) FROM ps_acad_plan
        """, ())
    row = db.fetchone()
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
    try:
        req = urllib.request.urlopen(url, timeout=30)
        jsondata = req.read()
        data = json.loads(jsondata)
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
    try:
        req = urllib.request.urlopen(url, timeout=30)
        jsondata = req.read()
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
    try:
        req = urllib.request.urlopen(url, timeout=30)
        jsondata = req.read()
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





