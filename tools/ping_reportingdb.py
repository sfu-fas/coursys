import socket

try:
    conn = socket.create_connection(('localhost', 50000), 30)
except Exception as e:
    print("Problem connecting to reporting database: SSH tunnel is probably down.")
    print("") 
    print(e)
