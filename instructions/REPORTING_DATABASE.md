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


## Reporting Database Tips

- Many fields are somewhat cryptic, but can be joined to a table that has more verbose explanations.
 These explanatory tables are generally suffixed `_tbl`. 
 For example, the `acad_prog` field for students' academic program is explained in `ps_acad_prog_tbl` and the field `visa_permit_type` field in the work visa tables is explained by rows in `ps_visa_permit_tbl`.
- In these (and other) tables, watch for the `eff_status` field that is either `'A'` (active) or `'I'` (inactive). There is also often an `effdt` and you have to select the most-recent active record for the correct data.
 For the `_tbl` descriptions, it is often easier to just pre-select the explainations and join in you logic, instead of adding horrible complexity to your SQL query just to get descriptions.
- Usually, fields with the same name hold the same value. For example `acad_org` is the department that owns the thing pretty much everywhere and values correspond to departments described in `ps_acad_org_tbl`. 
- Many tables have `effdt` and `effseq` fields to indicate when things were active and their order.
 So to select a student's academic program history, `SELECT * FROM ps_acad_prog WHERE emplid='...' ORDER BY effdt, effseq`. Selecting the One True Current Status out of a table like this is tricky.


## Access in Production




## Auth in Production

The production server must have authentication done by someone with Reporting Database access.

We have a sysadmin web UI to enter a username and password (/sysadmin/csrpt). That calls `coredata.csrpt.initial_csrpt_auth` which creates a kerberos keytab and `coredata.csrpt.refresh_csrpt_auth` to generate a ticket. A periodic task calls `refresh_csrpt_auth` to refresh the ticket every few hours. Those files are shared among the docker containers as the `csrpt_auth` volume.

The shell scripts `kinit.sh` and `kinit-refresh.sh` do these same steps. They shouldn't be necessary, but have been retained. They can be run in the admin container if necessary.


## More Auth Details

We are using Kerberos to authenticate to the MSSQL Server. Our kerberos workflow is based on [kerberos authentication](https://sfu.teamdynamix.com/TDClient/255/ITServices/KB/ArticleDet?ID=3932) from ITS. Authenticating to CSRPT as we do in production is a two-step process.

Step 0: `/etc/krb5.conf` is put in place by our Docker recipe, indicating how Kerberos authentication is to be done.

To start a keytab must be created representing a real user's authentication details: their username and password, and the type of authentication we need. This is done by the web UI that calls `initial_csrpt_auth` or manually with `kinit.sh`. That is stored (inside the container) as `/csrpt_auth/adsfu.keytab`. Both methods also execute step 2...

Next, `refresh_csrpt_auth` or `kinit-refresh.sh` uses that keytab file to request a ticket from the authentication server. This creates a `/tmp/krb4cc_${UID}` file, which we symlink to `/csrpt_auth/krb4cc`. The ticket has a modest lifespan, so this must be periodicly refreshed, but it can be done hands-free.

The `/csrpt_auth` directory is mounted on all containers that need CSRPT auth. When we use pyodbc to actually connect to CSRPT, it reads `/tmp/krb4cc_${UID}`.

