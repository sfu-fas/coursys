import sys, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')
from coredata.queries import SIMSConn
import pprint
import csv, datetime, functools, json, itertools, collections

# adapted from https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
def memoize(obj):
    global cache
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = obj.__name__ + '|' + str(args) + '|' + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer

CACHE_FILE = 'result_cache.json'
def dump_cache():
    global cache
    with open(CACHE_FILE, 'wb') as fp:
        json.dump(cache, fp, indent=1)
def load_cache():
    global cache
    try:
        with open(CACHE_FILE, 'rb') as fp:
            cache = json.load(fp)
    except IOError:
        cache = {}

@memoize
def plans_as_of(dt, emplids):
    db = SIMSConn()
    if not emplids:
        return []

    query = """SELECT emplid, stdnt_car_nbr, acad_plan
    FROM CS.PS_ACAD_PLAN A
    WHERE
       effdt=(SELECT MAX(effdt) FROM CS.PS_ACAD_PLAN WHERE emplid=A.emplid AND effdt<=%s)
       AND effseq=(SELECT MAX(effseq) FROM CS.PS_ACAD_PLAN WHERE emplid=A.emplid AND effdt=A.effdt)
       AND emplid IN %s
       ORDER BY emplid, plan_sequence"""
    db.execute(query, (dt, emplids))
    return [(emplid,[prog[2] for prog in progit]) for emplid,progit in itertools.groupby(db, lambda t: t[0])]


@memoize
def course_members(class_nbr, strm):
    db = SIMSConn()
    query = """SELECT s.emplid FROM ps_stdnt_enrl s
        WHERE s.class_nbr=%s and s.strm=%s and s.enrl_status_reason IN ('ENRL','EWAT')"""
    db.execute(query, (class_nbr, strm))
    return [emplid for emplid, in db]

def course_plans(class_nbr, strm, dt):
    return [(class_nbr, strm, emplid, ','.join(plans_as_of(dt, emplid))) for emplid in course_members(class_nbr, strm)]

@memoize
def all_courses(strm):
    db = SIMSConn()
    db.execute("""SELECT subject, catalog_nbr, class_section, class_nbr, campus, trm.term_begin_dt FROM ps_class_tbl cls, ps_term_tbl trm WHERE 
               cls.strm=trm.strm AND class_section LIKE '%%00' AND trm.acad_career='UGRD'
               AND cls.cancel_dt IS NULL AND cls.acad_org='COMP SCI'
               AND cls.strm=%s
               ORDER BY subject ASC, catalog_nbr ASC, class_section ASC""",
               (strm,))
    return list(db)

def semester_students(out, strm):
    courses = all_courses(strm)
    #courses = courses[:3]
    sem_start = courses[0][5]
    query_date = (datetime.datetime.strptime(sem_start, '%Y-%m-%d') + datetime.timedelta(days=21)).date()
    programs_seen = set()
    for subject, catalog_nbr, class_section, class_nbr, campus, term_begin_dt in courses:
        print(strm, subject, catalog_nbr, class_section)
        members = course_members(class_nbr, strm)
        plans = dict(plans_as_of(query_date, members))
        #rows = [[subject, catalog_nbr, class_section, campus, emplid, ','.join(plans[emplid])] for emplid in members]
        #out.writerows(rows)
        counts = collections.Counter(itertools.chain(*list(plans.values())))
        progs_str = " + ".join("%i*%s" % (count, prog) for prog, count in counts.most_common())
        out.writerow([strm, subject, catalog_nbr, class_section, campus, len(members), progs_str])
        programs_seen |= set(itertools.chain(*list(plans.values())))
    
    return programs_seen

@memoize
def plans_desc(acad_plans):
    db = SIMSConn()
    query = """SELECT acad_plan, trnscr_descr
               FROM PS_ACAD_PLAN_TBL apt
               WHERE eff_status='A' AND acad_plan IN %s
               AND effdt=(SELECT MAX(effdt) FROM PS_ACAD_PLAN_TBL WHERE acad_plan=apt.acad_plan)
               ORDER BY acad_plan"""
    
    acad_plans = list(acad_plans)
    db.execute(query, (acad_plans,))
    out = csv.writer(open("programs.csv", 'wb'))
    out.writerows(db)
    
    

def main():
    load_cache()
    db = SIMSConn()
    out = csv.writer(open("course_majors.csv", 'wb'))
    out.writerow(['Semester', 'Subject', 'Number', 'Section', 'Campus', 'Enrol', 'Programs'])
    
    programs_seen = set()
    for strm in [1111,1114,1117, 1121,1124,1127, 1131,1134,1137]:
        progs = semester_students(out, strm)
        programs_seen |= progs
    plans_desc(programs_seen)
    
    dump_cache()
    return
    
main()
