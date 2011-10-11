# functions to manipulate the SVN repositories
from django.conf import settings
from coredata.models import Member, repo_name
from groups.models import Group
import MySQLdb

SVN_TABLE = "subversionacl"

def _db_conn():
    dbconn = MySQLdb.connect(**settings.SVN_DB_CONNECT)
    return dbconn.cursor()

def all_repositories(offering):
    """
    Build list of all repositories active for this course offering (so we can know for sure which ones must change).
    
    Returns dictionary of repository name to (ro users, rw users)
    """
    if not settings.SVN_DB_CONNECT:
        # don't try if not configured
        return {}
    db = _db_conn()
    
    db.execute('SELECT `repository`, `read`, `readandwrite` FROM '+SVN_TABLE+' WHERE `repository` LIKE %s', ('%' + offering.subject.upper() + offering.number + '-' + offering.semester.name + '-%'))
    repos = {}
    for row in db:
        repo, ro, rw = row
        if ro:
            ro = ro.split(',')
        else:
            ro = ''
        if rw:
            rw = rw.split(',')
        else:
            rw = ''
        repos[repo] = (set(ro), set(rw))

    return repos


def update_repository(reponame, rw_userids, ro_userids):
    """
    Update/create this repository on punch.csil, with permissions as given.
    """
    if not settings.SVN_DB_CONNECT:
        # don't try if not configured
        return
    db = _db_conn()
    
    rw = ','.join(rw_userids)
    ro = ','.join(ro_userids)
    
    db.execute('SELECT count(*) FROM '+SVN_TABLE+' WHERE `repository`=%s', (reponame))
    count = db.fetchone()[0]
    if count == 0:
        # doesn't exist: create
        if len(rw_userids)==0 and len(ro_userids)==0:
            # don't create if not needed
            pass
        else:
            db.execute('INSERT INTO '+SVN_TABLE+' (`repository`, `emplid`, `read`, `readandwrite`, `modified`) VALUES (%s, %s, %s, %s, %s)', (reponame, '', ro, rw, 'Y'))
    else:
        # already there: update
        db.execute('UPDATE '+SVN_TABLE+' set `read`=%s, `readandwrite`=%s, `modified`=%s WHERE `repository`=%s', (ro, rw, 'Y', reponame))


def _repo_needs_updating(repos, reponame, rw, ro):
    "Does this repository need to be updated?"
    if reponame not in repos:
        # unknown repository: create
        return True
    else:
        # do we need to update?
        ro0,rw0 = repos[reponame]
        if ro != ro0 or rw != rw0:
            return True
    return False

def update_offering_repositories(offering):
    """
    Update the Subversion repositories for this offering
    """
    if not offering.uses_svn():
        return
        
    from coredata.tasks import update_repository_task    
    repos = all_repositories(offering)
    instr = set((m.person.userid for m in offering.member_set.filter(role__in=["INST","TA"]).select_related('person')))

    # individual repositories
    for m in offering.member_set.select_related('person', 'offering', 'offering__semester'):
        rw = set([m.person.userid])
        ro = set()
        if offering.indiv_svn():
            ro = instr
        if m.role == "DROP":
            rw = set([])
        reponame = repo_name(offering, m.person.userid)
        
        if _repo_needs_updating(repos, reponame, rw, ro):
            #print ">>>", reponame
            update_repository_task.delay(reponame, rw, ro)
        
    # group repositories
    groups = Group.objects.filter(courseoffering=offering).select_related('courseoffering')
    for g in groups:
        userids = set()
        reponame = repo_name(offering, g.svn_slug)
        for gm in g.groupmember_set.filter(confirmed=True).select_related('student__person'):
            userids.add(gm.student.person.userid)

        if _repo_needs_updating(repos, reponame, userids, instr):
            #print ">>>", reponame
            update_repository_task.delay(reponame, userids, instr)
