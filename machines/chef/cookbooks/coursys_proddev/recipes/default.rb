

# Mysql
# this is a default poorly-secured database.
package "mysql-server"

execute "create database" do 
    command "echo \"create database if not exists coursys_db;\" | mysql"
end

execute "grant privileges" do 
    command "echo \"grant all on coursys_db.* to 'coursys_user'@'localhost' identified by 'coursys_password';\" | mysql"
end

# remove mail server if installed by a previous version of recipes
execute "remove_postfix" do
    command "dpkg --purge postfix"
end

# put in the fake https certification
cookbook_file "self-ssl.key" do 
    path "/etc/nginx/cert.key"
    mode 0400
end

cookbook_file "self-ssl.pem" do 
    path "/etc/nginx/cert.pem"
    mode 0400
end

# configure local settings
cookbook_file "localsettings.py" do
    owner "coursys"
    path "/home/coursys/courses/courses/localsettings.py"
    action :create
end

# configure secrets
cookbook_file "secrets.py" do
    owner "coursys"
    path "/home/coursys/courses/courses/secrets.py"
    action :create
end

# set rabbitmq password
execute "rabbit add_user" do 
    user "rabbitmq"
    environment ({'HOME' => '/var/lib/rabbitmq'})
    command "rabbitmqctl add_user coursys supersecretpassword"
    ignore_failure true    
end

execute "rabbit add_vhost" do
    user "rabbitmq"
    environment ({'HOME' => '/var/lib/rabbitmq'})
    command "rabbitmqctl add_vhost myvhost"
    ignore_failure true    
end

execute "rabbit set_permissions" do
    user "rabbitmq"
    environment ({'HOME' => '/var/lib/rabbitmq'})
    command "rabbitmqctl set_permissions -p myvhost coursys \".*\" \".*\" \".*\""
end

execute "create DB" do
    cwd "/home/coursys/courses"
    command "make create_db"
end

execute "restart gunicorns" do
    cwd "/home/coursys/courses"
    command "make restart"
end
