This directory contains the Chef configuration for the build server,
currently living at coffee.fas.sfu.ca.

It sets up git, the git key-server, the git-list view server, sfu-cas, and jenkins.

(You can run a 'test' build server from Vagrant, if you'd like to fiddle with it.) 

There are some steps that are not yet part of the Chef script, which I've included as manual steps below.


== Manual Steps ==

1. sudo ln -s /home/git/repo /home/git/courses

2. Change the 'valid-sfu-user' directive in /var/www/keys/.htaccess to only allow users whom you
want to give direct access to the codebase. 

3. When you visit <your server>, SFU CAS may redirect you to the wrong location. In 
    sudo vim /etc/apache2/mods-enabled/zz_sfu_cas.conf
you can add the CASRootProxiedAs directive to indicate to CAS where to redirect you. 

=== Jenkins ===

This really SHOULD be a Chef script. But it isn't yet. 

1. Authentication
- Manage Jenkins
- Configure System
- Enable Security
  - Set: Access Control - Jenkins's own user database
    - Allow Users to Sign Up [yes]
- Set: Logged-in users can do anything
- Register yourself as a user
- Set: Access Control - Jenkins's own user database
  - Allow Users to Sign Up [no]

2. Plugins
- Manage Jenkins
- Manage Plugins
- Available
    - You might have to wait a little while for this list to appear. 
- Git Plugin [yes]
- Green Balls [yes]
- "Restart Jenkins When Installation Is Complete and no jobs are running"

3. Git defaults
- From the command line, sudo su jenkins
- git config --global user.name = "Jenkins"
- git config --global user.email = "jenkins@domain"

4. Create new job

- Called 'courses'
- Use the (local) git repository, /home/git/repo
- Check out
- Paste something like the following into the 'build script' area: 

    /var/lib/jenkins/workspace/courses/courses_environment/bin/pip install -r $WORKSPACE/build_deps/working_deps.txt;
    touch db.sqlite;
    rm -f $WORKSPACE/db.sqlite;
    yes "no" | /var/lib/jenkins/workspace/courses/courses_environment/bin/python manage.py syncdb;
    /var/lib/jenkins/workspace/courses/courses_environment/bin/python manage.py migrate;
    /var/lib/jenkins/workspace/courses/courses_environment/bin/python manage.py loaddata test_data;
    /var/lib/jenkins/workspace/courses/courses_environment/bin/python manage.py test;

- Run the build. It'll fail, but it'll check out the repo and create the workspace. 

5. In /var/lib/jenkins/workspace/courses, create a virtualenv.
    
    cd /var/lib/jenkins/workspace/courses
    virtualenv courses_environment

6. Run the build. It should pass, now. 
