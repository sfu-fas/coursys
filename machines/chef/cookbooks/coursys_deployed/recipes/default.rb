package "rabbitmq-server"
package "mysql-server"
package "mysql-client"
package "libmysqlclient-dev"

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/vagrant/"
    command "pip install -r /home/vagrant/courses/build_deps/deployed_deps.txt"
end
