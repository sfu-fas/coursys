

== Automated Jenkins configuration steps you need to figure out, dick ==
* git config username & password 

== Manual Jenkins configuration steps ==

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

3. Create new job
- point it at the git repository "http://..."
- 
