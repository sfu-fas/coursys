# TODO

* docs for prod setup
* update SYSADMIN.md
    * document new csrpt auth code
    * server messages in /data/dynamic_config and "docker compose kill -s SIGHUP app"
* do we need/want to restart celery and/or celerybeat in cron?
* need some protocol for regular dnf updates and docker pulls
* umask
* CSRPT access in production docs


# Notes

## CSRPT Authentication


Testing in the shell:
```
docker compose -f docker-compose-csrpt-test.yml build
docker compose -f docker-compose-csrpt-test.yml run csrpt-test bash
tsql -S ss-csrpt-db1.dc.sfu.ca -D CSRPT
SELECT * FROM PS_TERM_TBL WHERE ACAD_YEAR='2012'
go
```

Testing connection in Python:
```
docker compose -f docker-compose-csrpt-test.yml build
docker compose -f docker-compose-csrpt-test.yml run csrpt-test python3
```
```py
import pyodbc
(SIMS_DB_SERVER, SIMS_DB_NAME) = ('ss-csrpt-db1.dc.sfu.ca', 'CSRPT')
dbconn = pyodbc.connect("DRIVER={FreeTDS};SERVER=%s;PORT=1433;DATABASE=%s;Trusted_Connection=Yes" % (SIMS_DB_SERVER, SIMS_DB_NAME))
c = dbconn.execute("SELECT * FROM PS_TERM_TBL WHERE ACAD_YEAR='2012'", ())
list(c)
```


