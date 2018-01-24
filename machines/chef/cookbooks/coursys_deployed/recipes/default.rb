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
group "adm" do # nginx log dir is readable by adm
  action :modify
  members "coursys"
  append true
end
directory "/home/coursys" do
    owner "coursys"
    mode "00755"
    action :create
end

# Link /home/ubuntu/courses to /home/coursys/courses"
execute "link coursys" do
    command "ln -s /home/ubuntu/courses /home/coursys/courses"
    not_if do ::File.exists?('/home/coursys/courses/manage.py') end
end
execute "chmod courses" do
    command "chown -R coursys /home/ubuntu/courses"
    ignore_failure true
end

# static files directory
directory "/home/coursys/static" do
    owner "coursys"
    group "coursys"
    mode 00755
    action :create
end
directory "/home/ubuntu/static" do
    owner "coursys"
    group "coursys"
    mode 00755
    action :create
end

# MySQL
package "mysql-client"
package "libmysqlclient-dev"

# Frontend Server
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

# encrypted backups
package "duplicity"
package "libssl-dev"
package "libffi-dev"

# for pillow build
package "libjpeg-dev"
package "zlib1g-dev"
package "libpng12-dev"

# Dev tools
package "make"
package "vim"
package "git"
package "ack-grep"
package "screen"

package "dos2unix"

# collect static files
execute "static files" do
    user "coursys"
    cwd "/home/coursys/courses"
    command "./manage.py collectstatic --noinput"
end

# database backup directory
directory "/home/coursys/db_backup" do
    owner "coursys"
    group "coursys"
    mode 00700
    action :create
end

# elasticsearch
package "elasticsearch"
file '/etc/default/elasticsearch' do
  content "START_DAEMON=true\nRESTART_ON_UPGRADE=true\n"
end
cookbook_file "elasticsearch.yml" do
    path "/etc/elasticsearch/elasticsearch.yml"
end

service "elasticsearch" do
  action :restart
end

# Rabbit Configuration
cookbook_file "rabbitmq.conf" do
    path "/etc/rabbitmq/rabbitmq-env.conf"
end
cookbook_file "rabbit.conf" do
    path "/etc/rabbitmq/rabbit.conf"
end
execute "dos2unix" do
    command "dos2unix /etc/rabbitmq/rabbitmq-env.conf"
end
execute "rabbit_enable_management" do
    command "rabbitmq-plugins enable rabbitmq_management"
end
execute "kill_the_rabbit" do
    # sometimes the initial startup seems to not connect to the pid file
    cwd "/"
    command "killall rabbitmq-server; killall beam; killall beam.smp; killall epmd"
    ignore_failure true
end
service "rabbitmq-server" do
  action :restart
end

# misc system config
cookbook_file "stunnel.conf" do
    path "/etc/stunnel/stunnel.conf"
end
cookbook_file "stunnel-defaults" do
    path "/etc/default/stunnel"
end
execute "deny_coursys_ssh" do
    cwd "/"
    command "grep -q 'DenyUsers coursys'  /etc/ssh/sshd_config || (echo '\nDenyUsers coursys\nDenyUsers www-data' >> /etc/ssh/sshd_config)"
end
cookbook_file "forward" do
    path "/root/.forward"
    owner "root"
end
cookbook_file "forward" do
    path "/home/coursys/.forward"
    owner "coursys"
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
execute "celery-update-rc.d" do
    command "update-rc.d celeryd defaults"
end
service "celeryd" do
  action :restart
end
cookbook_file "logrotate-celery" do
    path "/etc/logrotate.d/celery"
    owner "root"
    mode "0644"
    action :create
end


# configure NGINX
execute "dh group" do
    # generate unique DH group, per https://weakdh.org/sysadmin.html
    command "openssl dhparam -out /etc/nginx/dhparams.pem 2048"
    creates("/etc/nginx/dhparams.pem")
end
cookbook_file "nginx_default.conf" do
    path "/etc/nginx/sites-available/default"
    action :create
end
cookbook_file "error503.html" do
    path "/usr/share/nginx/html/error503.html"
end

# purge supervisord
#execute "uninstall-supervisord" do
#    command "echo y | pip uninstall supervisor"
#    ignore_failure true
#end
#file "/etc/supervisord.conf" do
#  action :delete
#end
#file "/etc/init.d/supervisord" do
#  action :delete
#end
#file "/etc/logrotate.d/gunicorn" do
#  action :delete
#end
cookbook_file "rc.local" do
    path "/etc/rc.local"
    owner "root"
    mode "0755"
    action :create
end

# create a directory for the gunicorn log files
# directory "/var/log/gunicorn"
directory "/var/log/gunicorn" do
    owner "coursys"
    mode "00755"
    action :create
end
cookbook_file "logrotate-gunicorn" do
    path "/etc/logrotate.d/gunicorn"
    owner "root"
    mode "0644"
    action :create
end


# create a script to run and restart supervisord
cookbook_file "Makefile" do
    path "/home/coursys/courses/Makefile"
    owner "coursys"
    mode "0755"
    action :create
end

# gunicorn upstart config
#cookbook_file "gunicorn.conf" do
#    path "/etc/init/gunicorn.conf"
#    mode "0644"
#    action :create
#end

# gunicorn systemd config
cookbook_file "gunicorn.service" do
    path "/lib/systemd/system/gunicorn.service"
    mode "0644"
    action :create
end


execute "gunicorn-systemd" do
    command "systemctl enable gunicorn"
end

#start gunicorn
execute "gunicorn" do
    command "systemctl restart gunicorn || systemctl start gunicorn"
end
