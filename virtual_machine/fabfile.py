from __future__ import with_statement
from fabric.api import run, local, env, sudo, prompt, cd, hide, prefix
try:
    from local_settings import local_settings
except ImportError:
    from local_settings_example import local_settings

import getpass
import time

""" 
To run this file, you will need:

-python fabric ( pip install fabric ) 
-VirtualBox ( TODO: instructions  ) 
-A virtual machine with a vanilla Ubuntu Server installation.
 
Then, you will need to configure the local settings contained in local_settings_example.py
(preferably by copying them into local_settings.py and changing them without checking them in.) 

"""
    
env.hosts = ['127.0.0.1']
env.user = local_settings['username']
env.password = local_settings['password']
env.port = local_settings['ssh_tunnel_port']
env.warn_only = True

results = []

def clone():
    """ Clone a copy of our VM, leaving us with SSH access to a pristine computer. """
    
    results.append( local('VBoxManage clonevm "'+local_settings['vm_name']+'" --name "'+local_settings['cloned_vm_name']+'" --register --options keepallmacs') )
    map_ports()

def map_ports():
    """ Map all of the cloned VM's ports to localhost ports. 
        WARNING: This can only be done on a VM that is _off_ """

    # Forward localhost:2222 to the cloned vm's SSH
    forward_port( 'ssh', 22, local_settings['ssh_tunnel_port'] )

    for open_port_tuple in local_settings['open_ports']:
        rule_name, guest_port, host_port = open_port_tuple
        forward_port( rule_name, guest_port, host_port )

def forward_port( rule_name, guest_port, host_port ):
    """ Forward guest_vm:<guest_port> to localhost:<host_port> """
    results.append( local('VBoxManage modifyvm "'+local_settings['cloned_vm_name']+'" --natpf1 "'+rule_name+'",tcp,,'+str(host_port)+',,'+str(guest_port) ) );

def on():
    """ Activate the VM, headless (no visual access). """
    
    local('VBoxHeadless --startvm '+local_settings['cloned_vm_name']+' &')

def off():
    """ Power down the VM. """
    
    local('VBoxManage controlvm '+local_settings['cloned_vm_name']+' poweroff')

def clear():
    """ Destroy the VM. """
    
    results.append( local('VBoxManage unregistervm --delete '+local_settings['cloned_vm_name'] ) )

def config():
    """ Configure the VM. """

    username = local_settings['svn_username'] if local_settings['svn_username'] != '' else prompt("SVN username:")
    password = local_settings['svn_password'] if local_settings['svn_password'] != '' else getpass.getpass( prompt="SVN password: " )

    with hide('stdout'):
        results.append( sudo('apt-get update') )
    results.append( sudo('apt-get install -y ' + ' '.join(local_settings['apt_packages'])) )
    with hide('running'):
        results.append( run('yes "yes"| svn checkout '+local_settings['svn_location']+' --username '+username+' --password '+password) )
    results.append( run('virtualenv --distribute ' + local_settings['virtualenv'] ) )
    with cd(local_settings['svn_folder']):
        with prefix('source ../'+local_settings['virtualenv']+'/bin/activate'):
            results.append( sudo('pip install --index-url=http://asb-9905-01.fas.sfu.ca/simple/ -r '+local_settings['location_of_dependencies']) )
            results.append( run('python manage.py syncdb --noinput') )
            results.append( run('python manage.py migrate') )
            results.append( run('python manage.py loaddata test_data') )

def test():
    """ Run the tests """

    wall = '-Wall' if local_settings['use_wall_of_shame'] else ''

    with cd(local_settings['svn_folder']):
        with prefix('source ../'+local_settings['virtualenv']+'/bin/activate'):
            results.append( run('python '+wall+' manage.py test --verbosity ' + str(local_settings['test_verbosity'])) ) 

def runserver():
    """ Run the django server """
    
    with cd('courses'):
        with prefix('source ../'+local_settings['virtualenv']+'/bin/activate'):
            results.append( run('python manage.py runserver 0:8000 &') )

def complete_build():
    off()
    time.sleep( 10 )
    clear()
    time.sleep( 10 )
    clone()
    time.sleep( 10 )
    on()
    time.sleep( 10 )
    config()
    test()
    time.sleep( 2 )
    runserver()

    failure = True in [x.failed for x in results]

    if failure:
        print "FAILURE"
        exit(1)
    else:
        print "SUCCESS" 
        exit(0)



