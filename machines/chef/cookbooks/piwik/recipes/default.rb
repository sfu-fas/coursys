ROOT_PASSWD = 'somepassword'
ACCT_PASSWD = 'somepassword'

# Apache

package "libapache2-mod-php5"
package "php5-mysql"
package "php5-gd"
package "php5-geoip"

service "apache2" do
  supports :restart => true, :reload => true
end
execute "apache-ssl" do
    command "a2enmod ssl"
    creates "/etc/apache2/mods-enabled/ssl.load"
    notifies :restart, 'service[apache2]', :immediately
end
execute "apache-sslconf" do
    command "a2ensite default-ssl"
    creates "/etc/apache2/sites-enabled/default-ssl.conf"
    notifies :restart, 'service[apache2]', :immediately
end
execute "apache-nosslconf" do
    command "a2dissite 000-default"
    not_if do not ::File.exists?('/etc/apache2/sites-enabled/000-default.conf') end
    notifies :restart, 'service[apache2]', :immediately
end

# Piwik

package "unzip"
execute "piwik-download" do
    cwd "/opt"
    command "wget http://builds.piwik.org/piwik.zip"
    creates "/opt/piwik.zip"
end
execute "piwik-install" do
    cwd "/var/www/html/"
    command "unzip /opt/piwik.zip && rm 'How to install Piwik.html' && chown -R www-data.www-data /var/www/html/piwik"
    creates "/var/www/html/piwik/index.php"
end

# local MySQL server

package "mysql-server"
execute "mysql-root-password" do
    # make sure password isn't empty
    command "mysqladmin -u root password #{ROOT_PASSWD}"
    only_if "mysql -uroot" # i.e. only if we can log in with no password
end
execute "mysql-create-db" do
    command "echo \"CREATE DATABASE piwik;\" | mysql -uroot -p#{ROOT_PASSWD}"
    ignore_failure true # fails if db exists, or root password changed, or ...
end
execute "mysql-coursys-user" do
    command "echo \"CREATE USER 'piwik'@'localhost' IDENTIFIED BY '#{ACCT_PASSWD}'\" | mysql -uroot -p#{ROOT_PASSWD}"
    ignore_failure true # fails if user exists, or root password changed, or ...
end
execute "mysql-coursys-grant" do
    command "echo \"GRANT ALL PRIVILEGES ON piwik.* TO piwik@localhost\" | mysql -uroot -p#{ROOT_PASSWD}"
    ignore_failure true # fails if root password changed, or ...
end