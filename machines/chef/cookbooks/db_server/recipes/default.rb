ROOT_PASSWD = 'somepassword'
ACCT_PASSWD = 'somepassword'

package "mysql-server"

service "mysql" do
  supports :restart => true, :reload => true
end

cookbook_file "my.cnf" do
    path "/etc/mysql/my.cnf"
    notifies :restart, 'service[mysql]', :immediately
end

# TODO: listen remotely, but only for courses.cs

execute "mysql-root-password" do
    # make sure password isn't empty
    command "mysqladmin -u root password #{ROOT_PASSWD}"
    only_if "mysql -uroot" # i.e. only if we can log in with no password
end

execute "mysql-create-db" do
    command "echo \"CREATE DATABASE coursys;\" | mysql -uroot -p#{ROOT_PASSWD}"
    ignore_failure true # fails if db exists, or root password changed, or ...
end

execute "mysql-coursys-user" do
    command "echo \"CREATE USER 'coursys_user'@'localhost' IDENTIFIED BY '#{ACCT_PASSWD}'\" | mysql -uroot -p#{ROOT_PASSWD}"
    ignore_failure true # fails if user exists, or root password changed, or ...
end

execute "mysql-coursys-grant" do
    command "echo \"GRANT ALL PRIVILEGES ON coursys.* TO coursys_user@localhost\" | mysql -uroot -p#{ROOT_PASSWD}"
    ignore_failure true # fails if root password changed, or ...
end

# TODO: grant for courses.cs.sfu.ca