package 'ntp'
package 'mysql-server'
package 'mysql-client'
node_num = 0 # TODO: must be unique for each server

# TODO: postfix confix like coursys_true_production

template '/etc/mysql/mysql.conf.d/z_coursys.cnf' do
  mode '0644'
  variables({
    :node_num => node_num
  })
end

service 'mysql' do
  action :restart
end
