# MySQL
package "mysql-server"
package "mysql-client"
package "libmysqlclient-dev"

# Media Server
package "nginx"

package "make"

# Queue Server
package "rabbitmq-server"

# Cache Server
package "memcached"

# We need this to connect to things in our data center because BLAUGH 
package "stunnel4"

# Keep the time in sync
package "ntp"

# Dev tools
package "vim"
package "git"
package "screen"

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/vagrant/"
    command "pip install -r /home/vagrant/courses/build_deps/deployed_deps.txt"
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

# misc system config
cookbook_file "stunnel.conf" do
    path "/etc/stunnel/stunnel.conf"
end
cookbook_file "rabbitmq.conf" do
    path "/etc/rabbitmq/rabbitmq.conf"
end
execute "deny_coursys_ssh" do
    cwd "/"
    command "grep -q 'DenyUsers coursys'  /etc/ssh/sshd_config || (echo '\nDenyUsers coursys' >> /etc/ssh/sshd_config)"
end

# celery daemon
cookbook_file "celeryd-init" do
    path "/etc/init.d/celeryd"
    mode 0755
end
cookbook_file "celeryd-defaults" do
    path "/etc/default/celeryd"
end
execute "debconf_update" do
    cwd "/"
    command "chsh -s /bin/bash www-data"
end


# postfix mail server
package "postfix"
cookbook_file "package-config.txt" do
    path "/tmp/package-config.txt"
end
execute "debconf_update" do
    cwd "/"
    command "debconf-set-selections /tmp/package-config.txt"
end
execute "debconf_reconfigure" do
    cwd "/"
    command "rm /etc/postfix/main.cf /etc/postfix/master.cf ; dpkg-reconfigure -f noninteractive postfix"
end




# configure NGINX
cookbook_file "nginx_default.conf" do
    path "/etc/nginx/sites-available/default"
    action :create
end

# put in the fake https certification
cookbook_file "self-ssl.key" do 
    path "/etc/nginx/cert.key"
end

cookbook_file "self-ssl.pem" do 
    path "/etc/nginx/cert.pem"
end

# create a directory for the gunicorn log files
# directory "/var/log/gunicorn"
directory "/var/log/gunicorn" do 
    owner "vagrant"
    mode "00755"
    action :create
end

# create a script to run gunicorn
cookbook_file "Makefile" do
    path "/home/vagrant/courses/Makefile"
    owner "vagrant"
    mode "0755"
    action :create
end

# create supervisor to run gunicorn, nginx


# TODO for proddev environment:
# - create mysql database 'coursys' on localhost
# - GRANT ALL PRIVILEGES ON coursys.* to coursysuser@localhost IDENTIFIED BY 'coursyspassword';
# - syncdb, migrate
