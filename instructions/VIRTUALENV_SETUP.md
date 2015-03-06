# VirtualEnv Setup

For this, you'll need to be on a Linux-ish machine.

## Requirements

In order to install the coursys deps, you're going to need some packages.

    sudo apt-get install git python python-pip python-dev python-lxml libxslt1-dev sqlite3 zlib1g-dev

## Create the VirtualEnv

Create a virtualenv for the project and install the Python dependencies:

    virtualenv coursys
    cd coursys
    . bin/activate
    git clone git@github.com:sfu-fas/coursys.git coursys
    cd coursys
    pip install -r build_deps/working_deps.txt

Adding the `--upgrade` option might solve some problems if your system is
complaining because it is already packing some of these libraries from a
different python project.
(If that's the case, though, you might break that other project! That's
why virtualenv is a thing!)

Once you've got things installed locally, all of the instructions in the 
previous section about building the database, running the server,
and testing the code are still pretty much good to go. 

## Build a Test Database

First, create an empty SQLite database and populate it with tables:

    python manage.py migrate

We could stop here, but the site isn't too useful without test data. Good thing
we have a big bale of it! 

    python manage.py loaddata test_data
    python manage.py update_index

If you're ever done something awful to your database, you can steamroll it
and rebuild it with 

    rm db.sqlite
    python manage.py migrate
    python manage.py loaddata test_data
    python manage.py update_index

## Start the Server

Start the devel server:

    python manage.py runserver

And then take your browser to http://localhost:8000