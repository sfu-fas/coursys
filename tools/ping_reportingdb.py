import socket

try:
    conn = socket.create_connection(('localhost', 50000), 30)
except:
    print "Problem connecting to reporting database: SSH tunnel is probably down."