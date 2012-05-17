from __future__ import with_statement
from fabric.api import run, local, env, sudo, prompt, cd, hide, prefix
import getpass

""" 
To run this file, you will need:

-python fabric ( pip install fabric ) 
-VirtualBox ( TODO: instructions  ) 
-A virtual machine with a vanilla Ubuntu Server installation.
 
Then, you will need to configure the local settings below. ( TODO: external config file. )
"""

local_settings = {
    #The name of the VM to clone.
    #   Here, we're expecting a registered VirtualBox VM, containing a fresh installation of an Ubuntu server.
    'vm_name':'coursys_dev',
    
    #The name to assign to the clone of the VM
    #   This can be anything so long as you do not already have a VM with this name
    'cloned_vm_name':'coursys_dev_clone',

    #This user, on the guest VM, must have sudo-level access." 
    'username':'coursys',
    'password':'op[]',

    #We redirect localhost:<this_port> to guest_vm:22, for ssh. " 
    'ssh_tunnel_port':'2222',

    #Open the following ports on the server.
    # ('runserver', '8000', '9000') would redirect localhost:9000 to guest_vm:8000
    'open_ports':[
        ('django_runserver', '8000', '9000'),
        ('http', '80', '9080'),
        ('https', '443', '9443')
    ],

    #Packages to install on the remote server.
    'apt_packages':[
        'subversion',
        'python-pip',
        'python-virtualenv',
        'python-dev', 
        'python-lxml',
        'sqlite3',
        'libxml2-dev',
        'libxslt1-dev'
    ],
    
    #The location of our SVN repo.
    'svn_location': 'https://cs-svn.cs.sfu.ca/svn/courseman/trunk/courses/', 
    'svn_folder': 'courses',

    #Don't check-in with files in here. 
    'svn_username': '',
    'svn_password': '',

    #Looking for a pip dependencies file, here, within the svn folder. 
    'location_of_dependencies': 'build_deps/working_deps.txt',

    #The name of the python virtualenv into which we'll install all of our libraries.
    'virtualenv': 'courses_python_environment',

    #Use python -Wall when testing.
    'use_wall_of_shame':False,
   
    # 0 means no output.
    # 1 means normal output (default).
    # 2 means verbose output.
    # 3 means very verbose output.    
    'test_verbosity':2
}
    
env.hosts = ['127.0.0.1']
env.user = local_settings['username']
env.password = local_settings['password']
env.port = local_settings['ssh_tunnel_port']

def clone():
    """ Clone a copy of our VM, leaving us with SSH access to a pristine computer. """
    
    local('VBoxManage clonevm "'+local_settings['vm_name']+'" --name "'+local_settings['cloned_vm_name']+'" --register --options keepallmacs')
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
    local('VBoxManage modifyvm "'+local_settings['cloned_vm_name']+'" --natpf1 "'+rule_name+'",tcp,,'+str(host_port)+',,'+str(guest_port) );

def on():
    """ Activate the VM, headless (no visual access). """
    
    local('VBoxHeadless --startvm '+local_settings['cloned_vm_name']+' &')

def off():
    """ Power down the VM. """
    
    local('VBoxManage controlvm '+local_settings['cloned_vm_name']+' poweroff')

def clear():
    """ Destroy the VM. """
    
    local('VBoxManage unregistervm --delete '+local_settings['cloned_vm_name'] )

def config():
    """ Configure the VM. """

    username = local_settings['svn_username'] if local_settings['svn_username'] != '' else prompt("SVN username:")
    password = local_settings['svn_password'] if local_settings['svn_password'] != '' else getpass.getpass( prompt="SVN password: " )

    with hide('stdout'):
        sudo('apt-get update')
    sudo('apt-get install -y ' + ' '.join(local_settings['apt_packages']))
    with hide('running'):
        run('yes "yes"| svn checkout '+local_settings['svn_location']+' --username '+username+' --password '+password)
    run('virtualenv --distribute ' + local_settings['virtualenv'] )
    with cd(local_settings['svn_folder']):
        with prefix('source ../'+local_settings['virtualenv']+'/bin/activate'):
            sudo('pip install -r '+local_settings['location_of_dependencies'])
            run('python manage.py syncdb --noinput')
            run('python manage.py migrate')
            run('python manage.py loaddata test_data')

def test():
    """ Run the tests """

    wall = '-Wall' if local_settings['use_wall_of_shame'] else ''

    with cd(local_settings['svn_folder']):
        with prefix('source ../'+local_settings['virtualenv']+'/bin/activate'):
            run('python '+wall+' manage.py test --verbosity ' + str(local_settings['test_verbosity'])) 

def runserver():
    """ Run the django server """
    
    with cd('courses'):
        with prefix('source ../'+local_settings['virtualenv']+'/bin/activate'):
            run('python manage.py runserver 0:8000')

