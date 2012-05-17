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
