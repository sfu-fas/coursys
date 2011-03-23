
.. _converting-an-app:

Converting An App
=================

Converting an app to use South is very easy:

 - Edit your settings.py and put 'south' into `INSTALLED_APPS`
   (assuming you've installed it to the right place)
 
 - Run ``./manage.py syncdb`` to load the South table into the database.
   Note that syncdb looks different now - South modifies it.

 - Run ``./manage.py convert_to_south myapp`` - South will automatically make and
   pretend to apply your first migration.

Note that you'll need to convert before you make any changes; South detects
changes by comparing against the frozen state of the last migration, so it
cannot detect changes from before you converted to using South.
 
Converting other installations and servers
------------------------------------------

The convert_to_south command only works entirely on the first machine you run it
on. Once you've committed the initial migrations it made into your VCS,
you'll have to run ``./manage.py migrate myapp 0001 --fake`` on every machine that
has a copy of the codebase (make sure they were up-to-date with models and
schema first).

(For the interested, this is required because the initial migration that
convert_to_south makes will try and create all the existing tables; instead, you
tell South that it's already applied using --fake, so the next migrations
apply correctly.)

Remember that new installations of the codebase after this don't need these
steps; you need only do a syncdb then a normal migrate.
