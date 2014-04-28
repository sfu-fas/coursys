package "php5"

# create a /home/git directory
directory "/home/git" do
    mode "0755"
    action :create
end

# create a /var/git directory
directory "/var/git" do
    mode "0755"
end

execute "/etc/init.d/apache2 stop"

# create a git user
user "www-data" do
    home "/home/git"
    shell "/usr/bin/git-shell"
    action :manage
end

execute "/etc/init.d/apache2 start"

# create a ssh directory
directory "/home/git/.ssh" do
    owner "www-data"
    action :create
end

# add my key to the authorized_keys file
file "/home/git/.ssh/authorized_keys" do
    content "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC8/QDeDKfx+YNq8xIndzFnicnCi69IrgXckZbwbzmnfopVxYJsFG8cvQws+iyLb9Y/vv3PIQLt300BiX3DD488L8A9wr4mYzGsphWcuXIURN82uTw19iKL3W843WElbn9FOU9vuOSkljaCzzA1BxNAaOkE5S0Y3HIBnxFNUWpS22Yx1kJQNcF54ZOittGglzWmVDm8n77CpfaOcAvI1EJZnUkAYpVxwuuTdCzl415622rMS7pLP+Q7NpRwKBdE66cSgxCa+JUP+s3whpxLdK4PeRf/bXGAqZN6LUQy/rhboDeZejCjsxoaYQDPz625tTvs8RVfXjmohezJoNkalHqj classam@sfu.ca"
    owner "www-data"
    mode "0644"
end

# create a repository directory
directory "/home/git/repo" do
    owner "www-data"
    mode "0777"
    action :create
end

#initialize git repo
execute "git init --shared --bare" do
    user "www-data"
    cwd "/home/git/repo/"
end

#copy existing git repo
execute "cp -r /tmp/courses /var/git/repo"
execute "git remote add build /home/git/repo" do
    ignore_failure true
    cwd "/var/git/repo"
end
execute "git push build master" do 
    cwd "/var/git/repo"
end

#only a valid SFU user can access the repo
file "/var/www/.htaccess" do
    content "AuthType CAS
    require valid-sfu-user"
end

# create a symbolic link to git in the Apache directory
link "/var/www/repo.git" do
    to "/home/git/repo"
end

# update server info
execute "git update-server-info" do
    user "www-data"
    cwd "/home/git/repo/"
end

# accept http updates from authenticated users
execute "git config http.receivepack true" do
    user "www-data"
    cwd "/var/www/repo.git/"
end

# overwrite the default apache configuration with this one. 
template "#{node['apache']['dir']}/sites-available/default" do
  source "default-site.erb"
  owner "root"
  group node['apache']['root_group']
  mode 0644
end

directory "/var/www/keys" do 
    owner "www-data"
end

#only a valid SFU user can gain access to the git repository
file "/var/www/keys/.htaccess" do
    content "AuthType CAS
    require valid-sfu-user"
    owner "www-data"
end

# deploy the authorized-key gathering script 
cookbook_file "/var/www/keys/index.php" do
    owner "www-data"
    source "index.php"
end

directory "/var/www/gitlist"

# gitlist
remote_file "/var/www/gitlist/gitlist.tar.gz" do
    source "https://s3.amazonaws.com/gitlist/gitlist-0.2.tar.gz"
    action :create_if_missing
end

execute "tar -xvzf gitlist.tar.gz" do
    cwd "/var/www/gitlist"
end

template "/var/www/gitlist/config.ini" do
    source "gitlist-config.erb"
    owner "www-data"
    mode "0755"
    variables( {
        :apache_default_site => node[:apache_default_site]
    })
end

directory "/var/www/gitlist/cache" do
    owner "www-data"
    mode "0777"
end

# reboot apache
execute "/etc/init.d/apache2 restart"
