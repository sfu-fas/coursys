from __future__ import with_statement
from fabric.api import run, local, env, sudo
from fabric.operations import prompt
from fabric.context_managers import cd, hide, prefix
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
    ]
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
    # Forward localhost:2222 to the cloned vm's SSH
    forward_port( 'ssh', 22, local_settings['ssh_tunnel_port'] )

    #local('VBoxManage modifyvm "'+local_settings['cloned_vm_name']+'" --natpf1 "guestssh,tcp,,'+local_settings['ssh_tunnel_port']+',,22"')
    for open_port_tuple in local_settings['open_ports']:
        rule_name, guest_port, host_port = open_port_tuple
        forward_port( rule_name, guest_port, host_port )
    #    local('VBoxManage modifyvm "'+local_settings['cloned_vm_name']+'" --natpf1 "'+rulename+'",tcp,,'+host_port+',,'+guest_port );


def forward_port( rule_name, guest_port, host_port ):
    """ Forward guest_vm:<guest_port> to localhost:<host_port> """

    local('VBoxManage modifyvm "'+local_settings['cloned_vm_name']+'" --natpf1 "'+rule_name+'",tcp,,'+str(host_port)+',,'+str(guest_port) );
    


def on():
    """ Activate the VM, headless (no visual access). """
    
    local('VBoxHeadless --startvm '+local_settings['cloned_vm_name']+' &')

def off():
    """ Deactivate the VM. This is a poweroff, reasonably destructive, but I expect 'off' to be followed by 'clear', so ... """
    
    local('VBoxManage controlvm '+local_settings['cloned_vm_name']+' poweroff')

def clear():
    """ Destroy the VM. """
    
    local('VBoxManage unregistervm --delete '+local_settings['cloned_vm_name'] )

def config():
    """ Configure the VM. """

    username = prompt("SVN username:")
    password = getpass.getpass( prompt="SVN password: " )

    #sudo('apt-get update')
    sudo('apt-get install -y subversion python-pip python-virtualenv python-dev python-lxml sqlite3')
    with hide('running'):
        sudo('yes "yes"| svn checkout https://cs-svn.cs.sfu.ca/svn/courseman/trunk/courses/ --username '+username+' --password '+password)
    #run('virtualenv --distribute coursys_dev_environment')
    #with cd('courses'):
        #with prefix('source ../coursys_dev_environment/bin/activate'):
        #sudo('pip install -r build_deps/dependencies.txt')
        #run('yes "yes" | python manage.py syncdb')
        #run('python manage.py migrate')
        #run('python manage.py loaddata test_data')

def runserver():
    """ Run the django server """
    
    with cd('courses'):
        #with prefix('source ../coursys_dev_environment/bin/activate'):
        run('python manage.py runserver 0:8000')
    

