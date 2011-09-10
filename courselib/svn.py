# functions to manipulate the SVN repositories
from django.conf import settings
from coredata.models import Member
import MySQLdb
try:
    from celery.task import task
except ImportError:
    # if no Celery, make @task be a no-op
    def task(fn):
        return fn

SVN_TABLE = "subversionacl"

def _db_conn():
    dbconn = MySQLdb.connect(**settings.SVN_DB_CONNECT)
    return dbconn.cursor()

def all_repositories(semester):
    """
    Build list of all repositories active for this semester (so we can know for sure which ones must change).
    
    Returns dictionary of repository name to (ro users, rw users)
    """
    if not settings.SVN_DB_CONNECT:
        # don't try if not configured
        return {}
    db = _db_conn()
    
    db.execute('SELECT `repository`, `read`, `readandwrite` FROM '+SVN_TABLE+' WHERE `repository` LIKE %s', ('%-'+semester.name+'-%'))
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

def repo_name(offering, slug):
    return offering.subject.upper() + offering.number + '-' + offering.semester.name + '-' + slug

@task
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
        db.execute('INSERT INTO '+SVN_TABLE+' (`repository`, `emplid`, `read`, `readandwrite`, `modified`) VALUES (%s, %s, %s, %s, %s)', (reponame, '', ro, rw, 'Y'))
    else:
        # already there: update
        db.execute('UPDATE '+SVN_TABLE+' set `read`=%s, `readandwrite`=%s, `modified`=%s WHERE `repository`=%s', (ro, rw, 'Y', reponame))


