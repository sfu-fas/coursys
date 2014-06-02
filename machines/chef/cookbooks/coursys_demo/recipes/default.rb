# reconfigure NGINX for the demo server
cookbook_file "nginx_default.conf" do
    path "/etc/nginx/sites-available/default"
    action :create
end
service "nginx" do
  action :reload
end

# an appropriate localsettings
cookbook_file "localsettings.py" do
    path "/home/coursys/courses/courses/localsettings.py"
    owner "coursys"
    mode "0644"
    action :create
end
