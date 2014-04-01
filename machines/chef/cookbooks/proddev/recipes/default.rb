package "mysql-server"

# this is a default poorly-secured database.

execute "create database" do 
    command "echo \"create database if not exists coursys_db;\" | mysql"
end

execute "grant privileges" do 
    command "echo \"grant all on coursys_db.* to 'coursys_user'@'localhost' identified by 'coursys_password';\" | mysql"
end

# configure local settings
cookbook_file "localsettings.py" do
    path "/home/vagrant/courses/courses/localsettings.py"
    action :create
end

# configure secrets
cookbook_file "secrets.py" do
    path "/home/vagrant/courses/courses/secrets.py"
    action :create
end



