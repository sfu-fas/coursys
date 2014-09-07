
There are some parts of CourSys that are tied intimately to the SFU environment.

Authentication
--------------

Coursys authentication is provided through the university Single-Sign-On
system, which uses [CAS Authentication](en.wikipedia.org/wiki/Central_Authentication_Service).

Django has a lot of support for pluggable authentication infrastructures -
whatever your university uses, it's likely that there's something in the 
Django ecosystem that will allow you to enable some form of automatic or 
single-sign-on structure. 

In our case, we're using the [django-cas](https://bitbucket.org/cpcc/django-cas/overview)
package, which populates `request.user` and `request.user.username`.

In Coursys, the standard authentication User object is generally abandoned in
favour of the `coredata.models` "Person" object. This Person object is keyed to
an employee/student id ("301008183") and a user id ("classam"). This Person object is
used a _lot_ throughout Coursys, so if you're changing to a model where, 
for example, employee/student id doesn't exist, it might be wise to alter 
Person to provide emplid as a calculated property.

    @property
    def emplid(self):
        return self.userid


The Great Data Heist
--------------------

The system depends on certain coredata.models objects being generated
automatically by the system.

Namely, 
* Person (so that the system can reconcile SSO logins, which just
provide a userid like 'classam', with actual student data, containing things like
first name, last name, and student ID)
* Course objects ( a single course, so, "CMPT 101" )
* CourseOffering objects (a single offering
    of a course, so, "CMPT 101 in Fall 2016")
* Member objects (linking a Person to a CourseOffering - "classam" is a 
    student in "CMPT 101 in Fall 2016", "ggbaker" is a lecturer in 
    "CMPT 101 in Fall 2016")

No interface exists for creating these objects, as Coursys populates them
automatically from university data sources. The mechanics of this are laid out
in `coredata/importer.py` and `coredata/queries.py`.

The import run is idempotent. Successive runs should never create duplicate
data - which is important, because we run this import script _every single morning_.
