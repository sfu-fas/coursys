Here is a quick description of what is in the project:

COURSYS APPS
coredata: data on course offerings and enrolment; imported from goSFU or set by admins
  coredata/importer.py: program to do the import from goSFU
dashboard: responsible for display of front page, main course pages, news items
discipline: handling academic dishonesty cases
grades: management of course activities and grades
groups: handling groups so assignments can be group-based
log: finer-grained logging for the system
marking: finer-grained marking with a rubric
mobile: some read-only views for mobile devices
planning: planning of courses, assigning instructors, etc.
submission: submission of work (for later grading)
ta: management of TA applications and assignment
grad: grade student database
ra: research assistant database and appointments
advisornotes: advisor notepads for student advising

OTHER TOP-LEVEL FILES/DIRECTORIES
courselib: various library code for the system
docs: reports written on the system by DDP students
external: external code used by the system
media: static web files (CSS, JS, images, etc.)
old: practice/warmup modules written that are no longer used.
serialize.py: code to create more JSON data for test_data.json.  See comments in the file.
server-setup: description of how the production server is configured.
tools: various scripts that have been used to manage the data as necessary

Other files are the standard Django setup.

