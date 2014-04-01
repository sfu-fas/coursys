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

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/vagrant/"
    command "pip install -r /home/vagrant/courses/build_deps/deployed_deps.txt"
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

# create a script to run gunicorn
cookbook_file "Makefile" do
    path "/home/vagrant/courses/Makefile"
    owner "vagrant"
    mode "0755"
    action :create
end
