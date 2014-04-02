# MySQL
package "mysql-client"
package "libmysqlclient-dev"

# Media Server
package "nginx"

# Queue Server
package "rabbitmq-server"

# Cache Server
package "memcached"

# We need this to connect to things in our data center because BLAUGH 
package "stunnel4"

# Keep the time in sync
package "ntp"

# Dev tools
package "make"
package "vim"
package "git"
package "ack-grep"
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
    path "/etc/rabbitmq/rabbitmq-env.conf"
end

execute "deny_coursys_ssh" do
    cwd "/"
    command "grep -q 'DenyUsers coursys'  /etc/ssh/sshd_config || (echo '\nDenyUsers coursys\nDenyUsers www-data' >> /etc/ssh/sshd_config)"
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


#configure supervisord
cookbook_file "supervisord.conf" do 
    path "/etc/supervisord.conf"
    mode "0744"
end

# create a directory for the gunicorn log files
# directory "/var/log/gunicorn"
directory "/var/log/gunicorn" do 
    owner "vagrant"
    mode "00755"
    action :create
end

# create a script to run and restart supervisord
cookbook_file "Makefile" do
    path "/home/vagrant/courses/Makefile"
    owner "vagrant"
    mode "0755"
    action :create
end
