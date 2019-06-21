package ["git", "libxslt1-dev", "sqlite3", "zlib1g-dev", "libjpeg8-dev", "mercurial", "build-essential", "libmysqlclient-dev", 'npm']
package ["python3", "python3-pip", "python3-setuptools", "python3-dev", "python3-lxml", 'libffi-dev']

# pip install any listed requirements
execute "install_pip_requirements" do
    command "pip3 install -r /home/vagrant/courses/requirements.txt"
end

# throw ipython in there: we know it works on the VM
execute "install_ipython" do
    command "pip3 install ipython"
end

# build the locale that a few bits of the system rely on
execute "build_locale" do
    command "locale-gen en_CA.UTF-8"
end

# get node_modules
execute "node_modules" do
    cwd '/home/vagrant/courses'
    command "npm install"
end


package ['ruby', 'ruby-dev']
execute "github-markdown" do
    command "gem install commonmarker github-markup"
    not_if "ls /usr/local/bin/github-markup"
end
