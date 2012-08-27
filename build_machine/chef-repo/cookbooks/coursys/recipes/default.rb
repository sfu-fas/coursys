package "libxslt1-dev" do
    :install
end

package "python-dev" do
    :install
end

package "python-lxml" do
    :install
end

package "sqlite3" do
    :install
end

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/vagrant/courses"
    user "root"
    command "pip install -r /home/vagrant/courses/build_deps/working_deps.txt"
end

# python manage.py syncdb, migrate, load data
execute "syncdb" do
    cwd "/home/vagrant/courses"
    command "tools/reset_db.sh"
end

