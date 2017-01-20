apt_repository 'docker' do
  uri 'https://apt.dockerproject.org/repo/'
  components ['main']
  distribution 'ubuntu-trusty'
  key '58118E89F3A912897C070ADBF76221572C52609D'
  keyserver 'keyserver.ubuntu.com'
  action :add
  deb_src false
end

package 'docker-engine'