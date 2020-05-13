ubuntu_mirror = 'https://mirror.its.sfu.ca/mirror/ubuntu/'
ubuntu_release = `lsb_release -c`.split("\t")[1].strip
coursys_dir = node['coursys_dir'] || '/coursys'
coursys_repo = node['coursys_repo'] || 'https://github.com/sfu-fas/coursys.git'
coursys_branch = node['coursys_branch'] || 'master'
deploy_mode = node['deploy_mode'] || 'devel'
username = node['username']
user_home = "/home/#{username}/"
python_version = `python3 -c "import sys; print('%i.%i' % (sys.version_info.major, sys.version_info.minor))"`.strip
python_lib_dir = "/usr/local/lib/python#{python_version}/dist-packages"
data_root = '/data'

template '/etc/apt/sources.list' do
  variables(
    :mirror => ubuntu_mirror,
    :release => ubuntu_release
  )
  notifies :run, 'execute[apt-get update]', :immediately
end
execute 'apt-get update' do
  action :nothing
end
execute 'apt-get upgrade' do
  command 'apt-get dist-upgrade -y'
  only_if 'apt list --upgradeable | grep -q upgradable'
end

# basic requirements to run/build
package ['python3', 'python3-pip', 'git', 'mercurial', 'libmariadb-dev-compat', 'npm']
if deploy_mode == 'devel'
  package ['sqlite3']
end

# the code itself
directory coursys_dir do
  owner username
  mode '0755'
  recursive true
  action :create
end
execute "coursys_git" do
  cwd coursys_dir
  user username
  command "git clone --branch #{coursys_branch} #{coursys_repo} ."
  creates "#{coursys_dir}/manage.py"
end
template '/etc/profile.d/coursys-environment.sh' do
  variables(
    :coursys_dir => coursys_dir,
    :deploy_mode => deploy_mode,
    :data_root => data_root,
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

  for dir in ['', 'static', 'config', 'rabbitmq', 'elasticsearch', 'nginx-logs', 'mysql']
    directory "#{data_root}/#{dir}" do
      owner username
      mode '0755'
      action :create
    end
  end

  execute "django-status" do
    command "python3 manage.py collectstatic --no-input"
    cwd coursys_dir
    environment 'COURSYS_STATIC_DIR' => "#{data_root}/static"
    user username
    creates "#{data_root}/static/style/main.css"
  end

  # There was a conflict between npm and some mysql packages, so using the mariadb client, which should be equivalent.
  package ['mariadb-client', 'screen', 'nginx']
  service 'nginx' do
    action :nothing
  end
end

if deploy_mode == 'proddev'
  template "/etc/nginx/sites-available/default" do
    source 'nginx-proddev.conf.erb'
    variables(
      :coursys_dir => coursys_dir,
      :data_root => data_root,
    )
    notifies :restart, 'service[nginx]', :immediately
  end

end