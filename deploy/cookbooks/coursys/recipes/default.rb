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
rabbitmq_password = node['rabbitmq_password'] || 'supersecretpassword'
http_proxy = node['http_proxy']

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
package ['python3', 'python3-pip', 'git', 'mercurial', 'npm', 'libmariadb-dev-compat', 'libz-dev', 'unixodbc-dev', 'rsync']
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
    :http_proxy => http_proxy,
  )
end

# Python and JS deps
execute "install_pip_requirements" do
  command "python3 -m pip install -r #{coursys_dir}/requirements.txt"
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
  command 'gem install commonmarker -v 0.23.10 && gem install github-markup -v 4.0.2'
  creates '/usr/local/bin/github-markup'
end

if deploy_mode != 'devel'
  # some swap, so unused processes can get out of the way
  execute 'create swapfile' do
    command 'dd if=/dev/zero of=/swapfile bs=4096 count=1048576'
    creates '/swapfile'
  end
  execute 'swap-setup' do
    command 'chmod 0600 /swapfile && mkswap /swapfile && swapon /swapfile'
    not_if 'cat /proc/swaps | grep /swapfile'
  end
  execute 'fstab-swap' do
    command 'echo "/swapfile swap swap defaults 0 0" >> /etc/fstab'
    not_if 'cat /etc/fstab | grep /swapfile'
  end

  # docker
  execute 'docker-key' do
    command 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -'
  end
  directory "/lib/systemd/system/docker.service.d" do
    owner 'root'
    mode '0755'
    action :create
  end
  if !http_proxy.nil?
    template "/lib/systemd/system/docker.service.d/http-proxy.conf" do
      variables(
        :http_proxy => http_proxy,
      )
    end
  end
  apt_repository 'docker' do
    uri 'https://download.docker.com/linux/ubuntu/'
    components ['stable']
    distribution ubuntu_release
    arch 'amd64'
    #key '7EA0A9C3F273FCD8'
    #keyserver 'keyserver.ubuntu.com'
    action :add
    deb_src false
  end
  package ['docker', 'docker-compose']
  cookbook_file "/etc/docker/daemon.json" do
    source 'docker-daemon.json'
    owner "root"
    mode "0644"
  end
  execute "docker group" do
    command "gpasswd -a #{username} docker && service docker restart"
    not_if "grep docker /etc/group | grep #{username}"
  end
  execute "docker enable" do
    command "systemctl enable docker"
    creates "/etc/systemd/system/multi-user.target.wants/docker.service"
  end

  for dir in ['', 'static', 'config', 'rabbitmq', 'elasticsearch', 'nginx-logs', 'mysql', 'logs', 'db_backup']
    directory "#{data_root}/#{dir}" do
      owner username
      mode '0755'
      action :create
    end
  end
  directory "/data" do
    owner 'root'
    mode '0755'
    action :create
  end
  directory "/data/submitted_files" do
    owner username
    mode '0755'
    action :create
  end

  execute "pyopenssh-fix" do
    # this is a hack around a broken pip3 + pyOpenSSL install, per https://stackoverflow.com/a/74243128/6871666
    # It should only fire if currently needed (the "not_if" guard)
    command "wget https://files.pythonhosted.org/packages/54/a7/2104f674a5a6845b04c8ff01659becc6b8978ca410b82b94287e0b1e018b/pyOpenSSL-24.1.0-py3-none-any.whl -O /tmp/pyOpenSSL-24.1.0-py3-none-any.whl && python3 -m easy_install /tmp/pyOpenSSL-24.1.0-py3-none-any.whl"
    not_if "pip3 > /dev/null"
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

  #package 'snapd'
  #execute 'install-certbot' do
  #  command 'snap install --classic certbot'
  #  creates '/snap/bin/certbot'
  #end
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
  directory '/var/log/celery' do  # must be present, even though our logs are elsewhere
    mode '0755'
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
    minute '10'
    command ". /etc/profile.d/coursys-environment.sh; python3 /coursys/manage.py ping_celery"
  end
  cron "celery restart" do
    user 'root'
    minute '0'
    hour '7'
    command "systemctl restart celery celerybeat"
  end

  # nginx setup
  #execute "dh group" do
  #  # generate unique DH group, per https://weakdh.org/sysadmin.html
  #  command "openssl dhparam -out /etc/nginx/dhparams.pem 2048"
  #  creates("/etc/nginx/dhparams.pem")
  #end
  #cookbook_file '/etc/nginx/insecure.key' do
  #  mode 0400
  #end
  #cookbook_file '/etc/nginx/insecure.crt' do
  #  mode 0400
  #end

  #execute 'ssl_hands_off' do
  #  command 'grep -v "^\s*ssl_" /etc/nginx/nginx.conf > /tmp/nginx.conf && cp /tmp/nginx.conf /etc/nginx/nginx.conf'
  #  only_if 'grep -q "^\s*ssl_" /etc/nginx/nginx.conf'
  #end
  template "/etc/nginx/sites-available/_common.conf" do
    source 'nginx-common.conf.erb'
    variables(
      :coursys_dir => coursys_dir,
      :data_root => data_root,
    )
    notifies :restart, 'service[nginx]', :immediately
  end

  # the different personalities of nginx that we can deploy...
  if deploy_mode == 'proddev'
    serve_names = [domain_name, 'localhost']
    redirect_names = ['coursys-dev.selfip.net']
    #https_port = '443'
    #hsts = true  # TODO: re-enable when we're settled
    hsts = false
  end
  if deploy_mode == 'demo'
    serve_names = [domain_name]
    redirect_names = []
    #https_port = '443'
    #hsts = true  # TODO: re-enable when we're settled
    hsts = false
  end
  if deploy_mode == 'production'
    raise "We expect the canonical domain name to be coursys.sfu.ca here: adjust server_names if something changed." unless domain_name == 'coursys.sfu.ca'
    serve_names = ['coursys.sfu.ca', 'fasit.sfu.ca', 'coursys-prd.sfu.ca']  # TODO: coursys-prd should only be needed in transition
    redirect_names = ['coursys.cs.sfu.ca', 'courses.cs.sfu.ca']
    #https_port = '443'
    #hsts = true  # TODO: re-enable when we're settled
    hsts = false
  end

#   if deploy_mode == 'proddev'
#     # In proddev, use the insecure keys. In all other cases, demand that someone get a proper key in place, outside this recipe.
#     for name in serve_names+redirect_names do
#       directory "/etc/letsencrypt/live/#{name}" do
#         recursive true
#       end
#       cookbook_file "/etc/letsencrypt/live/#{name}/fullchain.pem" do
#         source 'insecure.crt'
#         mode 0400
#       end
#       cookbook_file "/etc/letsencrypt/live/#{name}/privkey.pem" do
#         source 'insecure.key'
#         mode 0400
#       end
#       cookbook_file "/etc/letsencrypt/live/#{name}/chain.pem" do
#         source 'insecure.crt'
#         mode 0400
#       end
#     end
#   end

  # create a partial config files /etc/nginx/sites-available/#{name}.conf for each domain name we handle
  for name in serve_names do
    template "/etc/nginx/sites-available/#{name}.conf" do
      source 'nginx-site.conf.erb'
      variables(
        :domain_name => name,
        #:https_port => https_port,
        :true_domain_name => domain_name,
        :data_root => data_root,
        :serve => true, # actually serve pages on this name
      )
    end
  end
  for name in redirect_names do
    template "/etc/nginx/sites-available/#{name}.conf" do
      source 'nginx-site.conf.erb'
      variables(
        :domain_name => name,
        #:https_port => https_port,
        :true_domain_name => domain_name,
        :data_root => data_root,
        :serve => false, # don't serve pages; redirect to https://domain_name
      )
    end
  end

  # main nginx config
  template "/etc/nginx/sites-available/default" do
    source 'nginx-nossl.conf.erb'
    variables(
      :hsts => hsts,
      :all_names => serve_names + redirect_names,
      :data_root => data_root,
      :true_domain_name => domain_name,
      #:https_port => https_port,
    )
    notifies :restart, 'service[nginx]', :immediately
  end

  # certbot renew: will fail when it runs if no certificate is in place
  #cron "certbot" do
  #  user 'root'
  #  hour 4
  #  minute 48
  #  weekday 0
  #  command "certbot renew"
  #end
end


if deploy_mode != 'devel'
  # CSRPT database connection
  cookbook_file '/opt/config/package-config.txt' do
  end
  execute "debconf_update" do
    command "debconf-set-selections /opt/config/package-config.txt"
  end
  package ['krb5-user', 'tdsodbc']
  cookbook_file "/etc/odbcinst.ini" do
    owner "root"
    mode "0644"
  end
  cron "kinit refresh" do
    user username
    minute '30'
    hour '*/2'
    command "/usr/bin/kinit `cat ~/kerberos/username`@AD.SFU.CA -k -t ~/kerberos/adsfu.keytab"
  end

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

  #execute "ssh_no_passwords" do
  #  command "echo '\nPasswordAuthentication no' >> /etc/ssh/sshd_config"
  #  not_if "grep -q '^PasswordAuthentication no' /etc/ssh/sshd_config"
  #  notifies :restart, 'service[ssh]', :immediately
  #end

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
