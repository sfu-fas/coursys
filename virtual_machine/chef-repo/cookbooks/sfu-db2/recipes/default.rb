
db_database = node[:sfu_db2][:database]
db_node = node[:sfu_db2][:node]
db_users = node[:sfu_db2][:users]

# deploy DB2 v9.7 tar file
cookbook_file "/tmp/db2.tar.gz" do
    source "v9.7fp5_linuxx64_client.tar.gz"
end

execute "tar -xvzf db2.tar.gz" do
    cwd "/tmp/"
    creates "client"
end

execute "yes \"no\" | /tmp/client/db2_install" do
    creates "/opt/ibm/db2/V9.7"
end

for db_user in db_users do

    if db_user == 'jenkins' then
        home = "/var/lib/jenkins"
        execute "sudo sh -c 'echo \"jenkins ALL=(vagrant) NOPASSWD: ALL\" >> /etc/sudoers'"
    else
        home = "/home/#{db_user}"
    end

    file "#{home}/.profile" do
        owner db_user
    end

    execute "/opt/ibm/db2/V9.7/instance/db2icrt -s client #{db_user}" do
        creates "#{home}/sqllib"
    end

    execute "#{home}/sqllib/bin/db2 catalog tcpip node #{db_node} remote localhost server 50000" do
        user db_user
        ignore_failure true    
    end

    execute "#{home}/sqllib/bin/db2 catalog database #{db_database} as #{db_database} at node #{db_node}" do
        user db_user
        ignore_failure true    
    end

    execute "#{home}/sqllib/bin/db2 terminate" do 
        user db_user
        ignore_failure true    
    end 

    execute "cp #{home}/.profile #{home}/.bashrc" do
        creates "#{home}/.bashrc"
    end
    
end

# Python DB2 libraries

package 'python-dev'

cookbook_file "/tmp/pydb2.tar.gz" do
    source "PyDB2_1.1.1-1.tar.gz"
end

execute "tar -xvzf pydb2.tar.gz" do
    cwd "/tmp/"
    creates "PyDB2_1.1.1"
end

execute "chmod u+x -R /tmp/PyDB2_1.1.1"

execute "ln -s /opt/ibm/db2/V9.7/lib64 /opt/ibm/db2/V9.7/lib" do
    creates "/opt/ibm/db2/V9.7/lib"
end

execute "python setup.py install" do
    cwd "/tmp/PyDB2_1.1.1"
end
