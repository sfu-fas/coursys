# postfix mail server
package "postfix"
directory "/home/coursys/config" do
    owner "coursys"
    mode "00755"
    action :create
end
cookbook_file "package-config.txt" do
    path "/home/coursys/config/package-config-trueprod.txt"
end
execute "debconf_update" do
    cwd "/"
    command "debconf-set-selections /home/coursys/config/package-config-trueprod.txt"
end
execute "debconf_reconfigure" do
    cwd "/"
    command "rm /etc/postfix/main.cf /etc/postfix/master.cf ; dpkg-reconfigure -f noninteractive postfix"
end
execute "postfix_configure" do
    cwd "/"
    command "sudo /usr/sbin/postconf -e \"inet_interfaces = loopback-only\""
end
service "postfix" do
  action :restart
end


# certbot config
apt_repository 'certbot' do
  uri          'http://ppa.launchpad.net/certbot/certbot/ubuntu'
  distribution 'xenial'
  components   ['main']
  keyserver    'keyserver.ubuntu.com'
  key '75BCA694'
  deb_src      false
end
#package 'python-certbot-nginx' # currently needs python-acme >=17.0 manually installed https://packages.ubuntu.com/artful/python-acme

# reconfigure NGINX with end-user properties
cookbook_file "nginx_base.conf" do
    path "/etc/nginx/sites-available/nginx_base.conf"
    action :create
end
cookbook_file "nginx_default.conf" do
    path "/etc/nginx/sites-available/default"
    action :create
end
service "nginx" do
  action :restart
end

# celery checking cron
cron "celery check" do
    user 'coursys'
    minute '0'
    command 'python ${HOME}/courses/manage.py ping_celery'
end