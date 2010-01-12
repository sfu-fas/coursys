Here is a quick description of what is in the project:

EXTERNAL APPS
autoslug: adds AutoSlugField field type
django_cas: CAS authentication
timezones: adds TimeZoneField field type; requires PyTZ
external: the original unpacked directories for the above modules (minus the core code)

COURSE MANAGEMENT APPS
coredata: data on course offerings and enrolment; imported from goSFU or set by admins
  coredata/importer.py: program to do the import from goSFU
  coredata/fake_importer.py: program to do the import from goSFU, faking some things for development.
dashboard: responsible for display of front page, main course pages, news items
grades: management of course grades

OTHER
initial_data.json: basic data: semesters from 1094 to 1107
test_data.json: data used for testing/devel
serialize.py: code to create more JSON data for test_data.json.  See comments in the file.
media: static web files (CSS, JS, images, etc.)

All other files are the standard Django setup.
