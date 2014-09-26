
Grad Students
=============

A significant portion of the system is devoted to the management and administration of Grad Students. 

Unlike with the undergrad modules, the Grad Students are not offered direct access to the Grad Student
data - instead, their interactions with the Grad System are mediated by Grad Student, TA, and RA administrators, 
using the following applications: 

    /grad
    /tacontracts
    /ta
    /ra

While, of course, it is possible for students who are not Our Grad Students to accept TA and RA posts in FAS
departments, the TA and RA systems are both at least aware of the Grad Student system, because we want to keep 
track of the money that we are paying FAS Grad Students. 

grad
----
The application for managing Grad Students and Programs. The key models are GradProgram and GradStudent.

One important thing to note is that a GradStudent record is not unique to a Student - an individual student
can have multiple GradStudent records, a topic so complicated that I think it deserves its own subheader.

### Multiple GradStudent Records

Yeah, there it is. 

Each student interaction with our department, as a single start-to-finish run, gets one GradStudent object.

Let's imagine two students. Al and Bette. 

Al applies for a CMPT PhD. His application is denied. This creates and closes one GradStudent record. 

Al applies for a CMPT Masters, and is accepted. This creates another GradStudent record.

Al completes the CMPT Masters, graduates, and leaves the university. This closes the previous GradStudent record.

Al applies for a CMPT PhD, is accepted, and graduates. This creates and closes another GradStudent record.

Bette applies for a CMPT Masters, and is accepted. This creates a GradStudent record. 

Bette transfers into CMPT PhD. This changes the program of the existing GradStudent record, and creates a
GradProgramHistory entry in that GradStudent record to record the move. 

Bette completes her CMPT PhD, graduates, and leaves the university. This closes her GradStudent record.

After all of these machinations, both Al and Bette have a CMPT PhD - but Al has three GradStudent records
where Bette only has one. 

### Importing Grad Students

So, it's the beginning of the semester, and you need to add some grad students to the system!

We have a script that pulls GradStudent records automatically from SIMS. 

Let's imagine that the current semester is 1157, and the unit is MSE

Simply run: 

    python manage.py new_grad_students --semester=1157 --unit=MSE

It might ask you to reconcile some grad student records with records that already exist.
95% of the time, new applications should mean new grad records, so the best option
is almost always "N".

The code for this lives in /grad/management/commands/new_grad_students.py. 

This should work with MSE, ENSC, or CMPT. For units that aren't MSE, ENSC, or CMPT, 
you may need to modify the code, which
contains a _hard-coded_ mapping between SIMS program codes (like "MSEPH") and CourSys GradPrograms 
(like GradProgram "Mechatronics PhD Program").

GradProgram objects have a config object that can contain the SIMS program code - which
means that maintaining a hardcoded mapping object is asinine, and this script could be
easily refactored to not have to do that anymore. 

_"Hey, wouldn't it be nice if this were automatic and scheduled?"_

Yes, disembodied voice. Yes it would be. Integrating this with the automatic grad update functionality in grad/models.py
would be a wonderful idea. 

### The adm_appl_nbr

In this code, the adm_appl_nbr - Admission Application Number - is used a lot. It's one of the few unique identifiers 
in the SIMS data that we can use to separate students into separate GradStudent records, as it uniquely identifies
a single student's set of application objects.

### Automatically Updating Grad Students

So, here's a strange thing that you probably need to know: CMPT manually keeps its grad students up to date, but 
ENSC and MSE use a system that (mostly works and) just updates GradStudent status from SIMS. 

A lot of the code for this is borrowed from the code for Importing Grad Students. Yep, they're good candidates for
being combined with one another.

The logical starting point for this exists within `grad.models.create_or_update_student`, which is the core logic
for building GradStudent objects. It is called regularly from coredata.importer.get_person_grad.

This code leans heavily on: 
 * coredata.queries.find_or_generate_person : which finds or generates a Person object in the system that matches the emplid
 * coredata.queries.get_timeline : which tries to guess at the entire grad history of a student by calling a bunch of 
    coredata.queries functions and mooshing their results together.
 * grad.models.split_timeline_into_groups:  which tries to group the timeline into sets that would constitute a GradStudent
 * grad.models.admission_records_to_grad_statuses: which converts SIMS admission codes into Grad Status codes. 
 * grad.models.GradStudent.create : which creates a GradStudent object
 * coredata.queries.get_supervisory_committee : which, given a date range, tries to guess a supervisory committee

Based on the number of times the words 'tries to guess' is used in that description, you might get the feeling that the
automatic grad updater is less than infallible. You would be entirely correct. 

ta and tacontracts
------------------
The `/ta` and `/tacontracts` applications both manage TA Contracts for a semester.  

_"Why are there two different applications, both offering up what appears to be exactly the same set of functionality?"_

Good question, disembodied voice!

The original `/ta` application was designed to replace the _entire TA workflow_ for the CMPT department - posting a 
CMPT TA Job Application, collecting applicant data, ranking applicants, creating contracts for successful applicants, 
and creating TUGS for those successful applicants. 

While this was 
stupendously useful for CMPT, getting the `/ta` application working for other departments proved difficult, as each 
department had a completely different TA hiring workflow that would need to be respected by the application. 

ENSC and MSE still wanted a way to keep track of Grad Contracts, but not one that was tied to the hiring policies of
CMPT. `/tacontracts` was designed to fill that need, with `/forms` suggested as the solution for complicated hiring
form management. `/tacontracts` was designed to be as department-neutral as possible - it only deals with the problem
of creating and tracking TA Contracts, and leaves the hiring procedure out. 

_"Couldn't you adapt the CMPT system to use the new, simplified TA Contracts system, without pulling out their hiring
and ranking logic? That way you'd only have one set of TAContracts to manage."_ 

The hiring and ranking logic in `/ta` is pretty deeply attached to the contracts logic. It would require taking
the application completely apart, which would mean months of fixing bugs. 

Honestly, I think that a better solution would be to migrate all departments to use `/forms` for hiring and
`/tacontracts` for contracts, and shutter the older system - but that's way in the future. First we have to get
ENSC and MSE to the point where they are happy using `/forms` for hiring.

### TUGS

_"So, both `/ta` and `/tacontracts` use the TUG model from `/ta`. That doesn't seem like very good system architecture.
You should have refactored TUGS out into its own application."_

I totally agree. I should have. 

ra
--

I... don't have a lot to say about the RA part of the app. It manages Research Associate posts. Works fine. Not a lot
of strange gotchas have appeared, here, yet. 
