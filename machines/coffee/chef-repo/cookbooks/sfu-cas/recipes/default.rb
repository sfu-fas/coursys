
#download & unpack sfu_cas module 
remote_file "/tmp/mod_auth_cas_sfu-1.0.8.10480.tar" do
    source "http://www.sfu.ca/content/dam/sfu/itservices/publishing/cas/mod_auth_cas_sfu-1.0.8.10480.tar"
    action :create_if_missing
end

execute "tar -xvf mod_auth_cas_sfu-1.0.8.10480.tar" do
	cwd "/tmp"
end

# we'll need these to build successfully
package "apache2-threaded-dev" 
package "openssl"

# build the package
execute "apxs2 -i -c mod_auth_cas.c" do 
	cwd "/tmp/mod_auth_cas_sfu-1.0.8.10480/src"
end

execute "chmod 644 /usr/lib/apache2/modules/mod_auth_cas.so"

remote_file "/etc/ssl/certs/ThawtePremiumServerBundleCA.pem" do
    source "http://www.sfu.ca/content/dam/sfu/itservices/publishing/cas/ThawtePremiumServerBundleCA.pem"
    owner "www-data"
    mode "0755"
	action :create_if_missing
end

directory "/usr/local/apache2" do 
    owner 'www-data'
end

directory "/usr/local/apache2/cas" do
    owner 'www-data'
end

# Why zz_sfu_cas? If the cas module doesn't load before ssl.load, it will fail.
# .. and the loading happens in alphabetical order. 
file "/etc/apache2/mods-available/zz_sfu_cas.load" do
	content "LoadModule auth_cas_module /usr/lib/apache2/modules/mod_auth_cas.so"
end

cas_root_proxied_as = node[:sfu_cas][:proxy_server] ? "\n\tCASRootProxiedAs " + node[:sfu_cas][:proxy_server] : '' 

# We're using a long Timeout and IdleTimeout, here. 
file "/etc/apache2/mods-available/zz_sfu_cas.conf" do
	content "<IfModule mod_auth_cas.c>
     CASVersion 2
     CASValidateServer On
     CASCertificatePath /etc/ssl/certs/ThawtePremiumServerBundleCA.pem
     CASAllowWildcardCert Off
     CASLoginURL https://cas.sfu.ca/cgi-bin/WebObjects/cas.woa/wa/login
     CASValidateURL https://cas.sfu.ca/cgi-bin/WebObjects/cas.woa/wa/serviceValidate
     CASTimeout " + node[:sfu_cas][:timeout_in_seconds].to_s() + "
     CASIdleTimeout " + node[:sfu_cas][:idle_timeout_in_seconds].to_s() + "
     CASTicketsURL https://cas.sfu.ca/cgi-bin/WebObjects/cas.woa/tickets
     CASCookiePath /usr/local/apache2/cas/" + cas_root_proxied_as + " 
</IfModule>"
end

execute "a2enmod ssl" 
execute "a2enmod zz_sfu_cas"

# auth_basic may conflict with SFU CAS authentication
file "/etc/apache2/mods-enabled/auth_basic.load" do
	action :delete
end 

# .htaccess files need to _work_ for SFU CAS to work. 
execute "sed -i 's/AllowOverride None/AllowOverride All/g' /etc/apache2/sites-enabled/000-default"
