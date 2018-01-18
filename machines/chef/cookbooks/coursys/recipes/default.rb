package ["git", "libxslt1-dev", "sqlite3", "zlib1g-dev", "libjpeg8-dev", "mercurial", "build-essential", "libmysqlclient-dev"]
package ["python3", "python3-pip", "python3-setuptools", "python3-dev", "python3-lxml"]

# pip install any listed requirements
execute "install_pip_requirements" do
    cwd "/home/ubuntu/"
    command "pip3 install -r /home/ubuntu/courses/requirements.txt"
end

# throw ipython in there: we know it works on the VM
execute "install_ipython" do
    cwd "/home/ubuntu/"
    command "pip3 install ipython"
end

# build the locale that a few bits of the system rely on
execute "build_locale" do
    command "locale-gen en_CA.UTF-8"
end

package ['ruby', 'ruby-dev']
execute "github-markdown" do
    command "gem install commonmarker github-markup"
    not_if "ls /usr/local/bin/github-markup"
end
