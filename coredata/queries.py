from coredata.models import Person, Semester, SemesterWeek, ComputingAccount, CourseOffering
from django.conf import settings
from django.db import transaction
from django.core.cache import cache
import re, hashlib, datetime, operator

multiple_breaks = re.compile(r'\n\n+')

class DBConn(object):
    """
    Singleton object representing DB connection. Implementes a big enough subset of PEP 249 for me.
    
    singleton pattern implementation from: http://stackoverflow.com/questions/42558/python-and-the-singleton-pattern
    
    Absolutely NOT thread safe.
    Implemented as a singleton to minimize number of times DB connection overhead occurs.
    Should only be created on-demand (in function) to minimize startup for other processes.
    """
    dbpass_file = settings.DB_PASS_FILE
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DBConn, cls).__new__(cls, *args, **kwargs)
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
            print ">>>", real_query
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
    sims_db = "csrpt"
    schema = "dbcsown"
    
    DatabaseError = None
    DB2Error = None

    def get_connection(self):
        passfile = open(self.dbpass_file)
        _ = passfile.next()
        _ = passfile.next()
        _ = passfile.next()
        simspasswd = passfile.next().strip()
        
        import DB2
        SIMSConn.DatabaseError = DB2.DatabaseError
        SIMSConn.DB2Error = DB2.Error
        dbconn = DB2.connect(dsn=self.sims_db, uid=self.sims_user, pwd=simspasswd)
        cursor = dbconn.cursor()
        cursor.execute("SET SCHEMA "+self.schema)
        return dbconn, cursor

    def escape_arg(self, a):
        """
        Escape argument for DB2
        """
        # Based on description of PHP's db2_escape_string
        if type(a) in (int,long):
            return str(a)
        if type(a) in (tuple, list):
            return '(' + ', '.join((self.escape_arg(v) for v in a)) + ')'
        
        # assume it's a string if we don't know any better
        a = unicode(a).encode('utf8')
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
        if isinstance(v, basestring):
            return v.strip().decode('utf8')
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
        except SIMSConn.DatabaseError:
            raise SIMSProblem, "could not connect to reporting database"
        except ImportError:
            raise SIMSProblem, "could not import DB2 module"
        except SIMSConn.DB2Error:
            raise SIMSProblem, "problem with reporting database connection"

    wrapped.__name__ = func.__name__
    return wrapped

def _args_to_key(args, kwargs):
    "Hash arguments to get a cache key"
    h = hashlib.new('md5')
    h.update(unicode(args))
    h.update(unicode(kwargs))
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
        # use emails to guess userid: if not found, leave unset and hope AMAINT has it on next nightly update
        if get_userid:
            userid = userid_from_sims(emplid)
        else:
            userid = None
        return {'emplid': emplid, 'last_name': last_name, 'first_name': first_name, 'middle_name': middle_name, 'userid': userid}


def add_person(emplid, commit=True, get_userid=True):
    """
    Add a Person object based on the found SIMS data
    """
    with transaction.commit_on_success():
        ps = Person.objects.filter(emplid=emplid)
        if ps:
            # person already there: ignore
            return ps[0]

        data = find_person(emplid, get_userid=get_userid)
        if not data:
            return

        p = Person(emplid=data['emplid'], last_name=data['last_name'], first_name=data['first_name'],
                   pref_first_name=data['first_name'], middle_name=data['middle_name'], userid=data['userid'])
        p.save()
    return p

@cache_by_args
@SIMS_problem_handler
def get_person_by_userid(userid):
    try:
        p = Person.objects.get(userid=userid)
    except Person.DoesNotExist:
        try:
            ca = ComputingAccount.objects.get(userid=userid)
            p = add_person(ca.emplid)
        except ComputingAccount.DoesNotExist:
            return None

    return p

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
        db.execute("SELECT apt.acad_plan, apt.descr, apt.trnscr_descr from "
                   "(select max(effdt) as effdt from ps_acad_plan where emplid=%s) as last, "
                   "(select effdt, max(effseq) as effseq from ps_acad_plan where emplid=%s GROUP BY effdt) as seq, "
                   "ps_acad_plan as ap, "
                   "ps_acad_plan_tbl as apt, "
                   "(select acad_plan, max(effdt) as effdt from ps_acad_plan_tbl GROUP BY acad_plan) as lastplan "
                   "WHERE (apt.acad_plan=ap.acad_plan AND last.effdt=ap.effdt AND seq.effdt=last.effdt AND seq.effseq=ap.effseq "
                   "AND apt.effdt=lastplan.effdt AND lastplan.acad_plan=ap.acad_plan "
                   "AND apt.eff_status='A' AND ap.emplid=%s)", (str(emplid), str(emplid), str(emplid)))
        #  AND apt.trnscr_print_fl='Y'
        for acad_plan, descr, transcript in db:
            label = transcript or descr
            prog = "%s (%s)" % (label, acad_plan)
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
    db = SIMSConn()
    offerings = CourseOffering.objects.filter(course=course).exclude(crse_id__isnull=True).order_by('-semester__name')
    if offerings:
        offering = offerings[0]
    else:
        return None
    
    data = {}
    crse_id = "%06i" % (offering.crse_id)
    db.execute("SELECT descr, ssr_component, course_title_long, descrlong FROM ps_crse_catalog WHERE eff_status='A' AND crse_id=%s ORDER BY effdt DESC FETCH FIRST 1 ROWS ONLY", (crse_id,))
    for shorttitle, component, longtitle, descrlong in db:
        data['shorttitle'] = shorttitle
        data['component'] = component
        data['longtitle'] = longtitle
        data['descrlong'] = descrlong
    
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
        cdata = dict(zip(fields, row))
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
        cdata = dict(zip(fields, row))
        return cdata
    return {'ext_org': '?'}


@cache_by_args
def get_reqmnt_designtn():
    """
    Get and cache requirement designations (to avoid joining yet another table).
    """
    db = SIMSConn()
    
    db.execute("SELECT r.rqmnt_designtn, r.descrshort FROM ps_rqmnt_desig_tbl r", ())
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
        rdata = dict(zip(fields, row))
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
        rdata = dict(zip(fields, row))
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
        rdata = dict(zip(fields, row))
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
    if not (isinstance(strm, basestring) and strm.isdigit() and len(strm)==4):
        raise ValueError, "Bad strm: " + repr(strm)
    oldsem = Semester.objects.filter(name=strm)
    if oldsem:
        return oldsem[0]

    db = SIMSConn()
    db.execute("SELECT strm, term_begin_dt, term_end_dt FROM ps_term_tbl WHERE strm=%s", (strm,))
    row = db.fetchone()
    if row is None:
        raise ValueError, "Not Found: %r" % (strm)
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
