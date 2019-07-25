# Database Replication

```bash
rsync -aP machines/chef/cookbooks/replica ubuntu@199.60.1.1:
ssh -R 127.0.0.1:3333:localhost:3333 ubuntu@199.60.17.1
ssh -L 127.0.0.1:3333:onara5.local:3308 -p24 ggbaker@coursys.sfu.ca
```

```bash
sudo apt install chef
sudo mkdir -p /var/chef/cookbooks/
sudo ln -sf /home/ubuntu/replica /var/chef/cookbooks/replica
sudo chef-solo -o replica
```

