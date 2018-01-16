
db_database = node[:sfu_db2][:database]
db_node = node[:sfu_db2][:node]
db_users = node[:sfu_db2][:users]

# deploy DB2 v9.7 tar file
directory "/opt" do
    mode "00755"
    action :create
end
#cookbook_file "/opt/db2.tar.gz" do
#    source "v9.7fp5_linuxx64_client.tar.gz"
#end
DB2_DOWNLOAD = "v9.7fp10_linuxx64_client.tar.gz"
execute "get_db2_driver" do
    cwd "/opt"
    command "false"
    not_if do ::File.exists?("/opt/db2.tar.gz") end
end

execute "tar -xvzf db2.tar.gz" do
    cwd "/opt/"
    creates "client"
end

execute "yes \"no\" | /opt/client/db2_install" do
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

package 'python3-dev'

execute "pip3 install ibm_db==2.0.7" do
    creates "/usr/local/lib/python3.5/dist-packages/ibm_db_dbi.py"
end


