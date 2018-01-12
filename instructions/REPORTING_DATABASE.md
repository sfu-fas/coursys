# Reporting Database Configuration

## DB2 Client

Some [instructions on reporting database](https://www.sfu.ca/irp/links/pdaug.html) connections are provided by the PDAUG group under the heading "Instructions for Connecting to CSRPT". These are for Windows, but were adapted here.

From the [DB2 downloads page](http://www-01.ibm.com/support/docview.wss?rs=71&uid=swg27007053), download
DB2 Version 10.5 fixpack 5, "IBM Data Server Client" for 64-bit Linux
(labelled DSClients-linuxx64-client-10.5.0.5-FP005 and you eventually get a file `v10.5fp5_linuxx64_client.tar.gz`).
We also keep a copy of this download of the production server (from the installation there): that might be an easier source.

Unpack the archive and run `./db2_install`.

Set up the reporting database catalog on your machine (ont-time stuff):

    ssh -L 127.0.0.1:50000:hutch.ais.sfu.ca:50000 -l youruserid -N pf.sfu.ca # in the background to provide the port forward
    . $HOME/sqllib/db2profile
    ~/sqllib/bin/db2 CATALOG TCPIP NODE csrpt REMOTE localhost SERVER 50000
    ~/sqllib/bin/db2 CATALOG DB csrpt AT NODE csrpt

The usual connection incantation is the `ssh` command above to get the port connected.

## Command Line Access

It's maybe not very practical, but you can at least test things by doing queries on the command line:

    . $HOME/sqllib/db2profile
    stty -echo; read -p "Password: " PW; echo; stty echo
    ~/sqllib/bin/db2 CONNECT TO csrpt USER youruserid USING $PW
    ~/sqllib/bin/db2 "SELECT * FROM dbcsown.PS_TERM_TBL WHERE ACAD_YEAR='2012'" # just a test

## SQuirreL

I have been using [SQuirreL](http://squirrel-sql.sourceforge.net/) for exploring things.

Download the "Install jar for Windows/Linux/others" and `java -jar squirrel-sql-...-standard.jar`.
I install the DB2 stuff there, but it doesn't seem to do any good.

After installation, I had to hit it a little to find the DB2 drivers. In the `squirrel-sql.sh` add this line to the bottom of the `buildCPFromDir` function:

    CP="$CP":"${HOME}/sqllib/java/db2java.zip"

Then use the `squirrel-sql.sh` to start things. To set up the alias, use the "IBM DB2 App Driver", URL "jdbc:db2:csrpt" and your campus username and password.

I usually start every session with this, to avoid having to prefix the name of every DB table:

    SET SCHEMA dbcsown

## Python DB2 Library

You will need the [ibm_db package](https://github.com/ibmdb/python-ibmdb) installed:

    sudo apt-get install python3-dev
    pip install ibm_db==2.0.7        # 2.0.8 has an installation bug

## CourSys setup

In `courses/localsettings.py`, make sure the reporting database is turned on (obviously don't do this for demos or other places non-trusted users will be accessing things freely):

    DISABLE_REPORTING_DB = False

In `courses/secrets.py`, add the connection info it needs:

    SIMS_USER = 'youruserid'
    SIMS_PASSWORD = 'yourpassword'

After that, your CourSys instance should be able to do reporting DB queries. This is checked by the admin panel's "Deployment Checks".

## Reporting Database Tips

- Many fields are somewhat cryptic, but can be joined to a table that has more verbose explanations.
 These explanatory tables are generally suffixed `_tbl`. 
 For example, the `acad_prog` field for students' academic program is explained in `ps_acad_prog_tbl` and the field `visa_permit_type` field in the work visa tables is explained by rows in `ps_visa_permit_tbl`.
- In these (and other) tables, watch for the `eff_status` field that is either `'A'` (active) or `'I'` (inactive). There is also often an `effdt` and you have to select the most-recent active record for the correct data.
 For the `_tbl` descriptions, it is often easier to just pre-select the explainations and join in you logic, instead of adding horrible complexity to your SQL query just to get descriptions.
- Usually, fields with the same name hold the same value. For example `acad_org` is the department that owns the thing pretty much everywhere and values correspond to departments described in `ps_acad_org_tbl`. 
- Many tables have `effdt` and `effseq` fields to indicate when things were active and their order.
 So to select a student's academic program history, `SELECT * FROM ps_acad_prog WHERE emplid='...' ORDER BY effdt, effseq`. Selecting the One True Current Status out of a table like this is tricky.
