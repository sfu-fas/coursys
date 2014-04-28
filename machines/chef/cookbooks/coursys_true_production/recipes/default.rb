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

# reconfigure NGINX with end-user properties
cookbook_file "nginx_default.conf" do
    path "/etc/nginx/sites-available/default"
    action :create
end
service "nginx" do
  action :restart
end
