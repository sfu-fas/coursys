# functions to manipulate the SVN repositories
from django.conf import settings
from coredata.models import Member, repo_name
import MySQLdb

SVN_TABLE = "subversionacl"

def _db_conn():
    dbconn = MySQLdb.connect(**settings.SVN_DB_CONNECT)
    return dbconn.cursor()

def _all_repositories(offering):
    """
    Build list of all repositories active for this course offering (so we can know for sure which ones must change).
    
    Returns dictionary of repository name to (ro users, rw users)
    """
    if not settings.SVN_DB_CONNECT:
        # don't try if not configured
        return {}
    db = _db_conn()
    
    db.execute('SELECT `repository`, `read`, `readandwrite` FROM '+SVN_TABLE+' WHERE `repository` LIKE %s', ('%' + offering.subject.upper() + offering.number[0:3] + '-' + offering.semester.name + '-%'))
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

def _in_another_section(offering, m):
    """
    Is this student in another section? (besides this one; not DROPped)
    
    Checks the fields that are represented in SVN repo names: subject, number,
    userid, and semester.
    """
    others = Member.objects.filter(person=m.person,
             offering__semester=m.offering.semester,
             offering__subject=m.offering.subject,
             offering__number=m.offering.number) \
             .exclude(offering=m.offering).exclude(role="DROP").count()
    return others>0

def _offering_instructors(offering):
    """
    Set of userids of instructors and TAs for this offering
    """
    return set((m.person.userid for m in offering.member_set.filter(role__in=["INST","TA","APPR"]).select_related('person')))

def update_offering_repositories(offering):
    """
    Update the Subversion repositories for this offering
    """
    if not offering.uses_svn():
        return

    repos = _all_repositories(offering)
    instr = _offering_instructors(offering)

    # individual repositories
    for m in offering.member_set.select_related('person', 'offering', 'offering__semester'):
        update_indiv_repository(offering, m, instr, repos)

    # group repositories
    from groups.models import Group
    groups = Group.objects.filter(courseoffering=offering).select_related('courseoffering')
    for g in groups:
        update_group_repository(offering, g, instr, repos)


def update_indiv_repository(offering, m, instr, repos):
    """
    Update repository for one member
    """
    if not offering.uses_svn():
        return

    from coredata.tasks import update_repository_task
    if m.person.userid is None:
        return
    rw = set([m.person.userid])
    ro = set()
    if offering.indiv_svn():
        ro = instr - rw
    if m.role == "DROP" or offering.component=="CAN":
        rw = set([])
    reponame = repo_name(offering, m.person.userid)
        
    if reponame not in repos and m.role=="DROP":
        # missing repo and dropped student is okay.
        return

    if _repo_needs_updating(repos, reponame, rw, ro):
        if m.role == "DROP" and _in_another_section(offering, m):
            # if student dropped this section, but is still in another, let that one win.
            return
        update_repository_task.delay(reponame, rw, ro)


def update_group_repository(offering, g, instr=None, repos=None):
    """
    Update repository for one group.
    
    Also called from GroupMember.save() to update repos when necessary.
    """
    if not offering.uses_svn():
        return

    from coredata.tasks import update_repository_task
    if instr is None or repos is None:
        # if called from GroupMember.save(), we won't have these for free
        repos = _all_repositories(offering)
        instr = _offering_instructors(offering)

    userids = set()
    reponame = repo_name(offering, g.svn_slug)
    for gm in g.groupmember_set.filter(confirmed=True).select_related('student__person'):
        if gm.student.person.userid is None:
            return
        if gm.student.role == "DROP":
            return
        userids.add(gm.student.person.userid)

    if _repo_needs_updating(repos, reponame, userids, instr):
        update_repository_task.delay(reponame, userids, instr)

