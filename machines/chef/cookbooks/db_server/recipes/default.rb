package "mysql-server"

cookbook_file "my.cnf" do
    path "/etc/mysql/my.cnf"
end

service "mysql" do
  action :reload
end

execute "mysql-root-password" do
    # make sure password isn't empty
    command "mysqladmin -u root password somepassword"
    only_if "mysql -uroot" # i.e. only if we can log in with no password
end

# TODO: user setup: root password and app user
# TODO: listen remotely, but only for courses.cs