ubuntu_mirror = 'https://mirror.rcg.sfu.ca/mirror/ubuntu/'
ubuntu_release = `lsb_release -c`.split("\t")[1].strip
coursys_dir = node['coursys_dir'] || '/coursys'
coursys_repo = node['coursys_repo'] || 'https://github.com/sfu-fas/coursys.git'
coursys_branch = node['coursys_branch'] || 'master'
deploy_mode = node['deploy_mode'] || 'devel'
domain_name = node['external_hostname'] || 'localhost'
username = node['username']
user_home = "/home/#{username}/"
python_version = `python3 -c "import sys; print('%i.%i' % (sys.version_info.major, sys.version_info.minor))"`.strip
python_lib_dir = "/usr/local/lib/python#{python_version}/dist-packages"
data_root = '/opt'
ip_address = node['ip_address'] || '127.0.0.1'
rabbitmq_password = node['rabbitmq_password'] || 'supersecretpassword'

raise 'Bad deploy_mode' unless ['devel', 'proddev', 'demo', 'production'].include?(deploy_mode)

#template '/etc/apt/sources.list' do
#  variables(
#    :mirror => ubuntu_mirror,
#    :release => ubuntu_release
#  )
#  notifies :run, 'execute[apt-get update]', :immediately
#end
execute 'apt-get update' do
  action :run
end
execute 'apt-get upgrade' do
  command 'apt-get dist-upgrade -y'
  only_if 'apt list --upgradeable | grep -q upgradable'
end

# basic requirements to run/build
package ['python3', 'python3-pip', 'git', 'mercurial', 'npm', 'libmariadb-dev-compat', 'libz-dev']
if deploy_mode == 'devel'
  package ['sqlite3']
end

# the code itself
user username do
  home user_home
  shell '/bin/bash'
  manage_home true
end
directory coursys_dir do
  owner username
  mode '0755'
  recursive true
  action :create
end
execute "coursys_git" do
  # if the code is mounted externally (by Vagrant or similar), this will leave it alone (because of the "creates" guard)
  cwd coursys_dir
  user username
  command "git clone --branch #{coursys_branch} #{coursys_repo} ."
  creates "#{coursys_dir}/manage.py"
end
template '/etc/profile.d/coursys-environment.sh' do
  variables(
    :coursys_user => username,
    :coursys_dir => coursys_dir,
    :deploy_mode => deploy_mode == 'demo' ? 'proddev' : deploy_mode,
    :data_root => data_root,
    :rabbitmq_password => rabbitmq_password,
  )
end

# Python and JS deps
execute "install_pip_requirements" do
  command "pip3 install -r #{coursys_dir}/requirements.txt"
  creates "#{python_lib_dir}/django/__init__.py"
end
execute "npm-install" do
  command "npm install"
  cwd coursys_dir
  environment 'HOME' => user_home
  user username
  creates "#{coursys_dir}/node_modules/jquery/package.json"
end

# build the locale that a few bits of the system rely on
execute 'build_locale' do
  command 'locale-gen en_CA.UTF-8'
  not_if 'locale -a | grep en_CA.utf8'
end

# ruby for markdown markup
package ['ruby', 'ruby-dev']
execute 'github-markdown' do
  command 'gem install commonmarker github-markup'
  creates '/usr/local/bin/github-markup'
end

if deploy_mode != 'devel'
  # docker
  apt_repository 'docker' do
    uri 'https://download.docker.com/linux/ubuntu/'
    components ['stable']
    distribution ubuntu_release
    arch 'amd64'
    key '7EA0A9C3F273FCD8'
    keyserver 'keyserver.ubuntu.com'
    action :add
    deb_src false
  end
  package ['docker', 'docker-compose']
  execute "docker group" do
    command "gpasswd -a #{username} docker && service docker restart"
    not_if "grep docker /etc/group | grep #{username}"
  end
  execute "docker enable" do
    command "systemctl enable docker"
    creates "/etc/systemd/system/multi-user.target.wants/docker.service"
  end

  for dir in ['', 'static', 'config', 'submitted_files', 'rabbitmq', 'elasticsearch', 'nginx-logs', 'mysql', 'logs', 'db_backup']
    directory "#{data_root}/#{dir}" do
      owner username
      mode '0755'
      action :create
    end
  end

  execute "django-static" do
    command "python3 manage.py collectstatic --no-input"
    cwd coursys_dir
    environment ({ 'COURSYS_STATIC_DIR' => "#{data_root}/static", 'COURSYS_DATA_ROOT' => data_root })
    user username
    creates "#{data_root}/static/static/style/main.css"
  end
  template "#{data_root}/static/503.html" do
  end

  package 'snapd'
  execute 'install-certbot' do
    command 'snap install --classic certbot'
    creates '/snap/bin/certbot'
  end
  # This recipe doesn't address actually *running* certbot.

  # There was a conflict between npm and some mysql packages, so using the mariadb client, which should be equivalent.
  package ['mariadb-client', 'screen', 'nginx', 'ntp', 'ntpdate']
  service 'nginx' do
    action :nothing
  end
  service 'ssh' do
    action :nothing
  end

  for service in ['gunicorn', 'celery', 'celerybeat']
    template "/etc/systemd/system/#{service}.service" do
      variables(
        :coursys_dir => coursys_dir,
        :username => username,
        :data_root => data_root,
      )
    end
    execute "systemctl enable #{service}" do
      creates "/etc/systemd/system/multi-user.target.wants/#{service}.service"
    end
  end
  template "#{data_root}/config/celery-environment" do
    variables(
      :coursys_user => username,
      :coursys_dir => coursys_dir,
      :username => username,
      :data_root => data_root,
    )
  end
  directory '/opt/run/celery' do
    owner username
    mode '0755'
    recursive true
    action :create
  end
  file "#{coursys_dir}/.env" do
    content "RABBITMQ_PASSWORD=#{rabbitmq_password}\n"
  end

  for service in ['gunicorn', 'celery', 'nginxcoursys']
    template "/etc/logrotate.d/#{service}" do
      source "logrotate-#{service}.erb"
      variables(
        :coursys_dir => coursys_dir,
        :username => username,
        :data_root => data_root,
      )
    end
  end
  # celery checking cron
  execute "cron.allow" do
    command "echo #{username} >> /etc/cron.allow"
    not_if "grep -q #{username} /etc/cron.allow"
  end
  cron "celery check" do
    user username
    minute '0'
    command "python3 #{coursys_dir}/manage.py ping_celery"
  end

  # nginx setup
  execute "dh group" do
    # generate unique DH group, per https://weakdh.org/sysadmin.html
    command "openssl dhparam -out /etc/nginx/dhparams.pem 2048"
    creates("/etc/nginx/dhparams.pem")
  end
  cookbook_file '/etc/nginx/insecure.key' do
    mode 0400
  end
  cookbook_file '/etc/nginx/insecure.crt' do
    mode 0400
  end

  execute 'ssl_hands_off' do
    command 'grep -v "^\s*ssl_" /etc/nginx/nginx.conf > /tmp/nginx.conf && cp /tmp/nginx.conf /etc/nginx/nginx.conf'
    only_if 'grep -q "^\s*ssl_" /etc/nginx/nginx.conf'
  end
  template "/etc/nginx/sites-available/_common.conf" do
    source 'nginx-common.conf.erb'
    variables(
      :coursys_dir => coursys_dir,
      :data_root => data_root,
    )
    notifies :restart, 'service[nginx]', :immediately
  end
  # certbot renew: will fail when it runs if no certificate is in place
  cron "certbot" do
    user 'root'
    hour 4
    minute 48
    weekday 0
    command "certbot renew"
  end
end

if deploy_mode == 'proddev'
  # proddev-specific nginx config
  template "/etc/nginx/sites-available/default" do
    source 'nginx-proddev.conf.erb'
    variables(
      :coursys_dir => coursys_dir,
      :data_root => data_root,
      :domain_name => domain_name,
      :https_port => '8443',
      :ip_address => ip_address,
    )
    notifies :restart, 'service[nginx]', :immediately
  end
end
if deploy_mode == 'demo'
  # demo-specific nginx config
  template "/etc/nginx/sites-available/default" do
    source 'nginx-demo.conf.erb'
    variables(
      :coursys_dir => coursys_dir,
      :data_root => data_root,
      :domain_name => domain_name,
      :https_port => '443',
      :ip_address => ip_address,
    )
    notifies :restart, 'service[nginx]', :immediately
  end
end
if deploy_mode == 'production'
  # production nginx config
  template "/etc/nginx/sites-available/default" do
    source 'nginx-production.conf.erb'
    variables(
      :coursys_dir => coursys_dir,
      :data_root => data_root,
      :domain_name => domain_name,
      :https_port => '443',
      :ip_address => ip_address,
    )
    notifies :restart, 'service[nginx]', :immediately
  end
end



if deploy_mode != 'devel'
  # SIMS database connection
  db2_client_download = 'v10.5fp11_linuxx64_client.tar.gz'
  # This repository doesn't provide db2_client_download because copyright.
  # It must be inserted into cookbooks/courses/files/ manually for this to sequence to fire.
  if File.file?(Chef::Config[:cookbook_path] + '/coursys/files/' + db2_client_download)
    cookbook_file "#{user_home}/#{db2_client_download}" do
      owner username
    end
  end

  execute "db2-unpack" do
    command "tar xf #{db2_client_download}"
    cwd user_home
    user username
    creates "#{user_home}/client/db2_install"
    only_if { ::File.file?("#{user_home}/#{db2_client_download}") } # if we don't have the client, skip
  end

  execute "i386-arch" do
    command "dpkg --add-architecture i386"
    notifies :run, 'execute[apt-get update]', :immediately
    not_if "grep -q i386 /var/lib/dpkg/arch"
  end

  package ['libpam0g:i386', 'libaio1', 'lib32stdc++6']
  # This fails when run from the recipe but succeeds at the command line. For reasons.
  #execute "db2-install" do
  #  command "./db2_install"
  #  cwd "#{user_home}/client/"
  #  user username
  #  environment 'HOME' => user_home
  #  creates "#{user_home}/sqllib/bin/db2"
  #  only_if { ::File.file?("#{user_home}/client/db2_install") } # if we don't have the client, skip
  #end

  # The MOSS source, as moss.zip is also not distributed here for copyright reasons.
  # It must be inserted into cookbooks/courses/files/ manually and should contain moss/moss.pl.
  if File.file?(Chef::Config[:cookbook_path] + '/coursys/files/moss.zip')
    cookbook_file "#{user_home}/moss.zip" do
      owner username
    end
  end
  execute "moss-unpack" do
    command "unzip moss.zip"
    cwd user_home
    user username
    creates "#{user_home}/moss/moss.pl"
    only_if { ::File.file?("#{user_home}/moss.zip") } # if we don't have the code, skip
  end

  execute "ssh_no_passwords" do
    command "echo '\nPasswordAuthentication no' >> /etc/ssh/sshd_config"
    not_if "grep -q '^PasswordAuthentication no' /etc/ssh/sshd_config"
    notifies :restart, 'service[ssh]', :immediately
  end

  cookbook_file "forward" do
    path "/root/.forward"
    owner "root"
  end
  cookbook_file "forward" do
    path "#{user_home}/.forward"
    owner username
  end
end

if deploy_mode == 'production'
  # this breaks VM setups where we expect to be able to "vagrant ssh" as the CourSys user
  execute "deny_coursys_ssh" do
    command "echo '\nDenyUsers #{username}\nDenyUsers www-data' >> /etc/ssh/sshd_config"
    not_if "grep -q '^DenyUsers #{username}' /etc/ssh/sshd_config"
    notifies :restart, 'service[ssh]', :immediately
  end
end
