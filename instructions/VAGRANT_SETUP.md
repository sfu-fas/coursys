# Vagrant Setup

This has the benefit that it should work on just about anything: Windows, Mac, Linux.

## Install VirtualBox

https://www.virtualbox.org/

## Install Vagrant

http://vagrantup.com/

## Create a Virtual Machine 

If you're running Git on your Windows machine, you can use the terminal
that comes with Git, "Git Bash", to run commands from within your code
directory. 

First `cd` into whatever directory coursys exists in on your machine, then: 

    cd machines/developer
    vagrant up

This will download a virtual machine from the internet, then install CourSys
and all dependencies on it. 

## Access the server

If you'd like to interact with your server, from your 'machines/developer'
directory, type:

    vagrant ssh

From within the virtual machine, you can navigate to your codebase - 
it exists at `/home/vagrant/courses`.

## Build a Test Database

Django is composed of Apps, each which contains a set of Models which are
converted into database tables when the application is installed. 

First, create an empty SQLite database and populate it with tables:

    python3 manage.py migrate

We could stop here, but the site isn't too useful without test data. Good thing
we have a big bale of it! 

    python3 manage.py loaddata fixtures/*.json
    python3 manage.py update_index

If you're ever done something awful to your database, you can steamroll it
and rebuild it with 

    rm db.sqlite
    python3 manage.py migrate
    python3 manage.py loaddata fixtures/*.json
    python3 manage.py update_index

## Run the server

So let's turn this thing on! 

    python3 manage.py runserver 0:8000

Wait, why are we doing that thing with the `0:8000` there? Well, by default, 
Django's development server only allows connections from the same server
that's running the development server - but that's our virtual machine. 
Unless we want to do debugging from the console using curl and links (which
we do not want to do), we must allow access from all IPs - which we could
specify with 0.0.0.0, which shortens to 0. 

As for the `:8000` bit, that just identifies the port that we're serving 
Django on. 

## Access the server

Okay, crack open a web browser (outside the VM) and navigate to:

    localhost:8000

## Modify the Code

Wherever you've checked out your codebase on your host machine - for example:

    C:\Users\Awesome\Code\courses

is mounted on the virtual machine, as 

    /home/vagrant/courses

So, you can work on the code from your host machine, using
[your favourite text editor](http://www.vim.org/index.php). 

## Run Tests

Okay, so, you've made some changes and you want to push them back to the
repository - but wait! There's more! 

Have you written tests in your_app/tests.py to cover the changes you've made?

Did you run the tests? 

From within the Virtual Machine, you can run all of the tests with 

    python3 manage.py test

Which takes forever, because it tests every nook and cranny of Coursys. So,
instead, you can test one individual application with: 

    python3 manage.py test yourapp

## Shut Down

At the end of the day, you're going to want to shut down the virtual machine -
otherwise it will sit around on your computer, an entire virtual computer, 
slogging up resources and generally slowing things down. 

You can exit the server with:

    exit

Which doesn't shut it down! It just closes your ssh connection to the VM.

You can turn off the VM by navigating to `machines/developer` and running:

    vagrant halt
