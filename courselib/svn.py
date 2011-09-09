# functions to manipulate the SVN repositories
from django.conf import settings
from coredata.models import Member
import MySQLdb

SVN_TABLE = "subversionacl"

def update_repository(offering, slug, rw_userids, ro_userids):
    """
    Update/create this repository on punch.csil, with permissions as given.
    """
    if not settings.SVN_DB_CONNECT:
        # don't try if not configured
        return

    dbconn = MySQLdb.connect(**settings.SVN_DB_CONNECT)
    db = dbconn.cursor()
    
    reponame = offering.subject.upper() + offering.number + '-' + offering.semester.name + '-' + slug
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
    
