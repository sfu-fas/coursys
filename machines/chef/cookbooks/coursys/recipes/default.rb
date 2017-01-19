package "git"
package "libxslt1-dev"
package "python"
#package "python-pip"
package "python-setuptools"
package "python-dev"
package "python-lxml"
package "sqlite3"
package "zlib1g-dev"
package "libjpeg8-dev" # for pillow build
package "mercurial"
package "build-essential"


#install the proper pip
execute "install_proper_pip" do
    command "easy_install pip"
end

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/ubuntu/"
    command "pip install -r /home/ubuntu/courses/build_deps/working_deps.txt"
end

# throw ipython in there: we know it works on the VM
execute "install_ipython" do
    cwd "/home/ubuntu/"
    command "pip install ipython"
end

# build the locale that a few bits of the system rely on
execute "build_locale" do
    command "locale-gen en_CA.UTF-8"
end

# Fix sqlite version where we trigger a bug
# This is probably fragile: will fail if sqlite3 updated in yakkety. I'm hoping the root problem will be fixed soon.
execute 'fix sqlite' do
    command "cd tmp && wget -nc http://mirrors.kernel.org/ubuntu/pool/main/s/sqlite3/sqlite3_3.14.1-1build1_amd64.deb && wget -nc http://mirrors.kernel.org/ubuntu/pool/main/s/sqlite3/libsqlite3-0_3.14.1-1build1_amd64.deb && wget -nc http://mirrors.kernel.org/ubuntu/pool/main/r/readline/libreadline7_7.0-0ubuntu2_amd64.deb && dpkg -i /tmp/*.deb"
end