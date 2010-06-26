
.. _tutorial-part-5:

Part 5: Teams and Workflow
==========================

Migrations are all about improving the workflow for the developers and database
administrators of projects, and we think it's very important that it doesn't add
too much overhead to your daily coding, while at the same time reducing headaches
caused by the inevitable changes in schema every project has.

Firstly, note that migrations aren't a magic bullet. If you've suddenly decided
you're going to rearchitect your entire database schema, it might well be easier
to not write migrations and just start again, especially if you have no
production sites using the code (if you do, you might find custom
serialisation/unserialisation to be a better way of saving your data).

With that in mind, migrations are really something you should be using the rest
of the time. Hopefully, the previous parts of the tutorial have got you familiar
with what can easily be achieved with them; we've tried to cover a good
percentage of use cases, and if you think something should be included, don't
hesitate to ask for it.


Developer Workflow
------------------

As a developer, you should be doing things in this order:

 - Make the change to your models.py file (and affected code, such as
   post_syncdb signal hooks)
 - Make the migration
 - Rinse, repeat.

Don't try to make migrations before you make the changes; this will both
invalidate the frozen model data on the migration and make startmigration --auto
think nothing has changed. If you're making a large change, and want to split it
over several migrations, do each schema change to models.py separately, then make
the migration, and then make the next small change.


Team Workflow
-------------

While migrations for an individual developer are useful, teams are perhaps the
real reason they exist. It's very likely more than one member of your team will
be making database changes, and migrations allow the other developers to apply
their schema changes effortlessly and reproducibly.

You should keep all of your migrations in a VCS (for obvious reasons), and
encourage developers to run ./manage.py migrate if they see a new migration come
in when they do an update or pull.

The issue with teams and migrations occurs when more than one person makes a
migration in the same timeslot, and they both get committed without the other
having been applied. This is analogous to two people editing the same file in a
VCS at the same time, and like a VCS, South has ways of resolving the problem.

If this happens, the first thing to note is that South will detect the problem,
and issue a message like this::

 Inconsistent migration history
 The following options are available:
     --merge: will just attempt the migration ignoring any potential dependency conflicts.

If you re-run migrate with ``--merge``, South will simply apply the migrations
that were missing out-of-order. This usually works, as teams are working on
separate models; if it doesn't, you'll need to look at the actual migration
changes and resolve them manually, as it's likely they'll conflict.

The second thing to note is that, when you pull in someone else's model changes
complete with their own migration, you'll need to make a new empty migration
that has the changes from both branches of development frozen in (if you've
used mercurial, this is equivalent to a merge commit). To do so, simply run::

 ./manage.py schemamigration --empty appname merge_models
 
*(Note that merge_models is just a migration name; change it for whatever you
like)*

The important message here is that *South is no substitute for team coordination*
- in fact, most of the features are there purely to warn you that you haven't
coordinated, and the simple merging on offer is only there for the easy cases.
Make sure your team know who is working on what, so they don't write migrations
that affect the same parts of the DB at the same time.


Complex Application Sets
------------------------

It's often the case that, with Django projects, there is a set of apps which
references each others' models.py files. This is, at its truest form, a
dependency, and to ensure your migrations for such sets of applications apply
sanely (i.e. the migrations that create the tables in one app happen before the
migration that adds ForeignKeys to them in another app), South has a
:ref:`Dependencies <dependencies>` feature. Once you've added dependencies to
your migrations, South will ensure all prerequisites of a migration are
applied before applying the migration itself.
