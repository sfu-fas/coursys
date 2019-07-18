username = 'ubuntu'
home = '/home/' + username

template_vars = {
    username: username,
    home: home,
    private_mount: home + '/Private',
    mysql_data: home + '/Private/mysql'
}

package ['apache2', 'mysql-server'] do
    action :purge
end

execute 'apt-update' do
    command 'apt update'
    action :nothing
end
execute 'docker-cert' do
    command 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -'
    not_if "apt-key list | grep 'Docker Release'"
end
execute 'docker-repo' do
    command 'add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"'
    notifies :run, 'execute[apt-update]', :immediately
    not_if "grep 'download.docker.com' /etc/apt/sources.list"
end

package ['ecryptfs-utils', 'docker-ce']

execute "docker-unmask" do
    command "systemctl unmask docker.service && systemctl unmask docker.socket && service docker start"
    not_if "systemctl list-unit-files | grep docker.service | grep enabled"
end
execute 'docker-compose' do
    command 'curl -L https://github.com/docker/compose/releases/download/1.17.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose'
    creates '/usr/local/bin/docker-compose'
end

group 'docker' do
    append true
    members [username]
    action :create
end

template "#{home}/start.sh" do
    variables(template_vars)
    owner username
    mode '0700'
end
template "#{home}/docker-compose.yml" do
    variables(template_vars)
    owner username
    mode '0600'
end

