package "libxslt1-dev"
package "python" 
package "python-pip"
package "python-dev"
package "python-lxml"
package "sqlite3" 

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/vagrant/"
    command "pip install -r /home/vagrant/courses/build_deps/working_deps.txt"
end
