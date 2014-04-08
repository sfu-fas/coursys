# postfix mail server
package "postfix"
cookbook_file "package-config.txt" do
    path "/tmp/package-config.txt"
end
execute "debconf_update" do
    cwd "/"
    command "debconf-set-selections /tmp/package-config.txt"
end
execute "debconf_reconfigure" do
    cwd "/"
    command "rm /etc/postfix/main.cf /etc/postfix/master.cf ; dpkg-reconfigure -f noninteractive postfix"
end
