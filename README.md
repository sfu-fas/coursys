
CourSys
=======

Installation
------------

### Installing Git

#### Ubuntu
    apt-get install git

#### Windows

Download and install Git for Windows from http://git-scm.com

#### Using Git

Here are some links on the git basics: 

* Super Sweet Interactive Tutorial: https://try.github.io/levels/1/challenges/1
* Basics: http://cworth.org/hgbook-git/tour/
* A More Complete Tutorial: http://www-cs-students.stanford.edu/~blynn/gitmagic/

Okay, so, use git to pull THIS repository. The one you're in. Yeah.

Good? Okay, let's continue. 

### Environment

There are a few different ways to install Coursys. 

The easiest and most cross-platform? Vagrant. 

#### Vagrant

##### Install VirtualBox

https://www.virtualbox.org/

##### Install Vagrant

http://vagrantup.com/

##### Create a Virtual Machine 

If you're running Git on your Windows machine, you can use the terminal
that comes with Git, "Git Bash", to run commands from within your code
directory. 

First `cd` into whatever directory coursys exists in on your machine, then: 

    cd machines/developer
    vagrant up

This will download a virtual machine from the internet, then install CourSys
and all dependencies on it. 

##### Access the server

If you'd like to interact with your server, from your 'machines/developer'
directory, type:

    vagrant ssh

From within the virtual machine, you can navigate to your codebase - 
it exists at `/home/vagrant/courses`.

##### Build a Test Database

Django is composed of Apps, each which contains a set of Models which are
converted into database tables when the application is installed. 

First, create an empty SQLite database and populate it with tables:

    python manage.py syncdb

Many of our longer-standing applications maintain South migrations - details of
such are here: http://south.readthedocs.org/ - but that means that we have to
apply all of the South modifications to the database before we continue:

    python manage.py migrate

We could stop here, but the site isn't too useful without test data. Good thing
we have a big bale of it! 

    python manage.py loaddata test_data

If you're ever done something awful to your database, you can steamroll it
and rebuild it with 

    rm db.sqlite
    python manage.py syncdb
    python manage.py migrate
    python manage.py loaddata test_data

##### Run the server

So let's turn this thing on! 

    python manage.py runserver 0:8000

Wait, why are we doing that thing with the `0:8000` there? Well, by default, 
Django's development server only allows connections from the same server
that's running the development server - but that's our virtual machine. 
Unless we want to do debugging from the console using curl and links (which
we do not want to do), we must allow access from all IPs - which we could
specify with 0.0.0.0, which shortens to 0. 

As for the `:8000` bit, that just identifies the port that we're serving 
Django on. 

##### Access the server

Okay, crack open a web browser and navigate to:

    localhost:8001

Why 8001? Well, because I had something running on port 8000 when I wrote
this. I mean *cough cough* to demonstrate how Vagrant handles port forwarding!

The file `machines/developer/Vagrantfile` controls the Virtual Machine - and
the line: 

    config.vm.forward_port 8000, 8001

controls the port-forwarding behavior of the VM.

##### Modify the Code

Wherever you've checked out your codebase on your host machine - for example:

    C:\Users\Awesome\Code\courses

is mounted on the virtual machine, as 

    /home/vagrant/courses

So, you can work on the code from your host machine, using
[your favourite text editor](http://www.vim.org/index.php). 


##### Run Tests

Okay, so, you've made some changes and you want to push them back to the
repository - but wait! There's more! 

Have you written tests in your_app/tests.py to cover the changes you've made?

Did you run the tests? 

From within the Virtual Machine, you can run all of the tests with 

    python manage.py test

Which takes forever, because it tests every nook and cranny of Coursys. So,
instead, you can test one individual application with: 

    python manage.py test yourapp

##### Shut Down

At the end of the day, you're going to want to shut down the virtual machine -
otherwise it will sit around on your computer, an entire virtual computer, 
slogging up resources and generally slowing things down. 

You can exit the server with:

    exit

Which doesn't shut it down! It just closes your ssh connection to the VM.

You can turn off the VM by navigating to `machines/developer` and running:

    vagrant halt


##### Change The Test Data

See `serialize.py` and the comments therein. 

If you modify the model for an app, you can reset the database with 

    python manage.py reset <appname>

##### Change The Environment

The configuration file that determines the properties of the generated machine
lives at `machines/developer/Vagrantfile`.

The file that loads the Coursys environment lives at
`machines/chef/cookbooks/coursys/recipes/default.rb`

But the real moneymaker is `build_deps/working_deps.txt`, which determines
which pip libraries are loaded when the environment is created. 

#### Ubuntu

Don't need no steenking virtual machine? You're already running Ubuntu on
your development machine? 

[Good work, soldier](http://i.imgur.com/OsT790T.gif).

In order to install the coursys deps, you're going to need some packages.

    sudo apt-get install git python python-pip python-dev python-lxml libxslt1-dev sqlite3 zlib1g-dev

Then you're going to need to use pip to install the Python deps - you're
also welcome to wrap this in a [virtualenv](http://virtualenv.readthedocs.org/en/latest/)
if that floats your boat. 

    pip install -r build_deps/working_deps.txt

Adding the `--upgrade` option might solve some problems if your system is
complaining because it is already packing some of these libraries from a
different python project.
(If that's the case, though, you might break that other project! That's
why virtualenv is a thing!)

Once you've got things installed locally, all of the instructions in the 
previous section about building the database, running the server,
and testing the code are still pretty much good to go. 

#### Gentoo/FreeBSD

[Oh, you'd like to install CourSys on Gentoo or FreeBSD, huh?](http://i0.kym-cdn.com/photos/images/newsfeed/000/198/010/tysonreaction.gif)

### Notable Test Data

* An instructor: ggbaker
* A system administrator: sumo
* An advisor: dzhao
* Some Grad students: 0aaagrad, 0bbbgrad, 0cccgrad...
* Some Undergrad students: 0aaa0... 0aaa19, 0bbb0...0bbb19... 

Table of Contents
-----------------

Here is a quick description of what is in the project:

### APPS
coredata: data on course offerings and enrolment; imported from goSFU or set by admins
  coredata/importer.py: program to do the import from goSFU
dashboard: responsible for display of front page, main course pages, news items
discipline: handling academic dishonesty cases
grades: management of course activities and grades
groups: handling groups so assignments can be group-based
log: finer-grained logging for the system
marking: finer-grained marking with a rubric
mobile: some read-only views for mobile devices
submission: submission of work (for later grading)
ta: management of TA applications and assignment
tacontracts: management of TA contracts 
grad: grade student database
ra: research assistant database and appointments
advisornotes: advisor notepads for student advising
discuss: discussion forum for course offerings
pages: wiki-like course web pages
onlineforms: configurable and fillable online forms
alerts: automated student problem alerts
planning: planning of courses, assigning instructors, etc.
techreq: collection of technical requirements for courses
booking: booking system for advisors

### OTHER TOP-LEVEL FILES/DIRECTORIES
courselib: various library code for the system
docs: reports written on the system by DDP students
external: external code used by the system
media: static web files (CSS, JS, images, etc.)
old: practice/warmup modules written that are no longer used.
serialize.py: code to create more JSON data for test_data.json.  See comments in the file.
server-setup: description of how the production server is configured.
tools: various scripts that have been used to manage the data as necessary

Other files are the standard Django setup.

