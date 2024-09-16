# Reporting Database Configuration

## MS SQL Client

Access to the Reporting Database (CSRPT) is authenticated with Kerberos.
That means you must `kinit` to initially authenticate, and occasionally `kinit -R` to renew the ticket.

We use FreeTDS to connect to CSRPT. It comes with `tsql` as a command-line client.
```shell
kinit username@AD.SFU.CA
tsql -S ss-csrpt-db1.dc.sfu.ca -D CSRPT
```

You can type queries, and `go` to run them.
```
1> SELECT * FROM PS_TERM_TBL WHERE ACAD_YEAR='2012'
2> go
```


## CourSys setup

In `courses/localsettings.py`, make sure the reporting database is turned on (obviously don't do this for demos or other places non-trusted users will be accessing things freely):

    DISABLE_REPORTING_DB = False
    SIMS_DB_SERVER = 'ss-csrpt-db1.dc.sfu.ca'

After that, your CourSys instance should be able to do reporting DB queries. This is checked by the admin panel's "Deployment Checks".

## Auth in Production

The production server must have [kerberos authentication](https://sfu.teamdynamix.com/TDClient/255/ITServices/KB/ArticleDet?ID=3932) done by someone with Reporting Database access. On the server, that can be done like this:
```shell
sudo su -l coursys
/coursys/kinit.sh
```
Enter your username and password when prompted. This creates authentication details in `~/kerberos` that are used by a cron job to regularly refresh the ticket.


## Reporting Database Tips

- Many fields are somewhat cryptic, but can be joined to a table that has more verbose explanations.
 These explanatory tables are generally suffixed `_tbl`. 
 For example, the `acad_prog` field for students' academic program is explained in `ps_acad_prog_tbl` and the field `visa_permit_type` field in the work visa tables is explained by rows in `ps_visa_permit_tbl`.
- In these (and other) tables, watch for the `eff_status` field that is either `'A'` (active) or `'I'` (inactive). There is also often an `effdt` and you have to select the most-recent active record for the correct data.
 For the `_tbl` descriptions, it is often easier to just pre-select the explainations and join in you logic, instead of adding horrible complexity to your SQL query just to get descriptions.
- Usually, fields with the same name hold the same value. For example `acad_org` is the department that owns the thing pretty much everywhere and values correspond to departments described in `ps_acad_org_tbl`. 
- Many tables have `effdt` and `effseq` fields to indicate when things were active and their order.
 So to select a student's academic program history, `SELECT * FROM ps_acad_prog WHERE emplid='...' ORDER BY effdt, effseq`. Selecting the One True Current Status out of a table like this is tricky.
