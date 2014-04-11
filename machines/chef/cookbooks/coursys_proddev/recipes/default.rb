package "mysql-server"

# this is a default poorly-secured database.

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
    path "/home/coursys/courses/courses/localsettings.py"
    action :create
end

# configure secrets
cookbook_file "secrets.py" do
    path "/home/coursys/courses/courses/secrets.py"
    action :create
end



