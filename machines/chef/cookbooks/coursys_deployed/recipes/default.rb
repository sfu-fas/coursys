# Create 'coursys' user
user "coursys" do
    home "/home/coursys"
    action :create
    shell "/bin/bash"
end

directory "/home/coursys" do
    owner "coursys"
    mode "00755"
    action :create
end

# Move /home/vagrant/courses to /home/coursys/courses"
execute "copy coursys" do
    command "cp -r /home/vagrant/courses /home/coursys/courses"
end

directory "/home/coursys/courses" do 
    owner "coursys"
    mode "00755"
    recursive true
    action :create
end

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
    path "/home/coursys/courses/courses/localsettings.py"
    action :create
end

# elasticsearch
package "openjdk-7-jre-headless"
execute "install_elasticsearch" do
    cwd "/home/coursys/config"
    command "wget -nc https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.1.0.deb && dpkg -i elasticsearch-1.1.0.deb && /etc/init.d/elasticsearch restart"
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

#put supervisord in init.d
cookbook_file "supervisor_init.d" do
    path "/etc/init.d/supervisord"
    mode "0755"
end

#start supervisord
execute "supervisord" do
    command "supervisord"
    ignore_failure true    
end

# create a directory for the gunicorn log files
# directory "/var/log/gunicorn"
directory "/var/log/gunicorn" do 
    owner "www-data"
    mode "00755"
    action :create
end

# create a script to run and restart supervisord
cookbook_file "Makefile" do
    path "/home/coursys/courses/Makefile"
    owner "coursys"
    mode "0755"
    action :create
end

# restart nginx
execute "restart nginx" do
    command "/etc/init.d/nginx restart"
end
