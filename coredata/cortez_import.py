import sys, os
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from coredata.queries import SIMSConn, DBConn

import pymssql, MySQLdb
import json

# in /etc/freetds/freetds.conf: [http://www.freetds.org/userguide/choosingtdsprotocol.htm]
# [global]
#    tds version = 7.0

class CortezConn(DBConn):
    db_host = '127.0.0.1'
    db_user = "fas.sfu.ca\\ggbaker"
    db_name = "ra"
    def escape_arg(self, a):
        return "'" + MySQLdb.escape_string(str(a)) + "'"

    def get_connection(self):
        passfile = open(self.dbpass_file)
        _ = passfile.next()
        _ = passfile.next()
        _ = passfile.next()
        pw = passfile.next().strip()

        conn = pymssql.connect(host=self.db_host, user=self.db_user,
             password=pw, database=self.db_name)
        return conn, conn.cursor()


def table_columns(dbname, table):
    db = CortezConn()
    db.execute("USE "+dbname, ())
    db.execute("select column_name, data_type, is_nullable, character_maximum_length from information_schema.columns where table_name=%s order by ordinal_position", (table,))
    return list(db)

def table_rows(dbname, table):
    db = CortezConn()
    db.execute("USE "+dbname, ())
    db.execute("SELECT * FROM "+table, ())
    return list(db)

def tables(dbname):
    db = CortezConn()
    db.execute("USE "+dbname, ())
    db.execute("SELECT name FROM sysobjects WHERE xtype='U'", ())
    return [n for n, in db]

def databases():
    db = CortezConn()
    db.execute("SELECT name FROM master..sysdatabases", ())
    return [n for n, in db]

import pprint
from django.core.serializers.json import DjangoJSONEncoder
print databases()
print tables('grad')
print table_columns('grad', 'Scholarships')
for r in table_rows('grad', 'Scholarships'):
    print r
#print table_columns('ra', 'sysobjects')
#print json.dumps( dump_table('ra', 'Contract'), cls=DjangoJSONEncoder, indent=1 )

#tasearch
#esp
#ra
#grad
#graddb
