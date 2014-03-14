# MySQL
package "mysql-server"
package "mysql-client"
package "libmysqlclient-dev"

# Media Server
package "nginx"

# WSGI Server
package "gunicorn"

# Queue Server
package "rabbitmq-server"

# Cache Server
package "memcached"

# We need this to connect to things in our data center because BLAUGH 
package "stunnel4"

# Keep the time in sync
package "ntp"

# To update the code
package "git"

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/vagrant/"
    command "pip install -r /home/vagrant/courses/build_deps/deployed_deps.txt"
end

# TODO
#  - move nginx to port 8000
#  - create startup script to run gunicorn on port 80
#     gunicorn wsgi --bind 0.0.0.0:80
