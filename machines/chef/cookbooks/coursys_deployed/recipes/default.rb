
# Create 'coursys' user
user "coursys" do
    home "/home/coursys"
    action :create
    shell "/bin/bash"
end
group "admin" do
  action :modify
  members "coursys"
  append true
end
directory "/home/coursys" do
    owner "coursys"
    mode "00755"
    action :create
end

# Link /home/vagrant/courses to /home/coursys/courses"
execute "link coursys" do
    command "ln -s /home/vagrant/courses /home/coursys/courses"
    not_if do ::File.exists?('/home/coursys/courses/manage.py') end
end
execute "chmod courses" do 
    command "chown -R coursys /home/vagrant/courses"
    ignore_failure true    
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
service "memcached" do
  action :restart
end

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

package "dos2unix"

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/vagrant/"
    command "pip install -r /home/vagrant/courses/build_deps/deployed_deps.txt"
end

# elasticsearch
package "openjdk-7-jre-headless"
directory "/tmp/elasticsearch" do
    owner "coursys"
    group "coursys"
    mode 00755
    action :create
end
execute "install_elasticsearch" do
    cwd "/tmp/elasticsearch"
    command "wget -nc https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.1.0.deb && dpkg -i elasticsearch-1.1.0.deb"
    not_if do ::File.exists?('/var/lib/elasticsearch/') end
end
cookbook_file "elasticsearch.yml" do
    path "/etc/elasticsearch/elasticsearch.yml"
end
service "elasticsearch" do
  action :restart
end

#Rabbit Configuration
cookbook_file "rabbitmq.conf" do
    path "/etc/rabbitmq/rabbitmq-env.conf"
end
execute "dos2unix" do
    command "dos2unix /etc/rabbitmq/rabbitmq-env.conf"
end
execute "kill_the_rabbit" do
    # sometimes the initial startup seems to not connect to the pid file
    cwd "/"
    command "killall rabbitmq-server; killall beam"
    ignore_failure true
end
service "rabbitmq-server" do
  action :restart
end

# misc system config
cookbook_file "stunnel.conf" do
    path "/etc/stunnel/stunnel.conf"
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
execute "dos2unix" do
    command "dos2unix /etc/init.d/celeryd"
end
cookbook_file "celeryd-defaults" do
    path "/etc/default/celeryd"
end
execute "dos2unix" do
    command "dos2unix /etc/default/celeryd"
end
execute "update-rc.d" do
    command "update-rc.d celeryd defaults"
end
execute "wwwdata_shell" do
    cwd "/"
    command "chsh -s /bin/bash www-data"
end
service "celeryd" do
  action :restart
end

# configure NGINX
cookbook_file "nginx_default.conf" do
    path "/etc/nginx/sites-available/default"
    action :create
end
service "nginx" do
  action :restart
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

# create a directory for the gunicorn log files
# directory "/var/log/gunicorn"
directory "/var/log/gunicorn" do 
    owner "coursys"
    mode "00766"
    action :create
end

# create a script to run and restart supervisord
cookbook_file "Makefile" do
    path "/home/coursys/courses/Makefile"
    owner "coursys"
    mode "0755"
    action :create
end

#start supervisord
execute "supervisord" do
    command "supervisord"
    ignore_failure true    
end
