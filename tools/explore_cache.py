import memcache
import socket

mc = memcache.Client(['127.0.0.1:22122'], debug=0)

#stats = mc.get_stats()[0][1]
#for k in stats:
#    print k, stats[k]


def get_slab(mc, slab):
    data = []
    for s in mc.servers:
        if not s.connect(): continue
        if s.family == socket.AF_INET:
            name = '%s:%s (%s)' % ( s.ip, s.port, s.weight )
        else:
            name = 'unix:%s (%s)' % ( s.address, s.weight )
        s.send_cmd('stats cachedump %s 100' % (slab))
        serverData = {}
        data.append(( name, serverData ))
        readline = s.readline
        while 1:
            line = readline()
            if not line or line.strip() == 'END': break
            stats = line.split(' ', 2)
            serverData[stats[1]] = stats[2]
    return(data)


slabs = mc.get_slabs()[0][1]
keys = set()
for slab in slabs:
     for key in get_slab(mc, slab)[0][1]:
         keys.add(key)

keys = list(keys)
for i,k in enumerate(keys):
    print(i,k)

n = int(input("Key: "))
print(">>>", keys[n])
print(mc.get(keys[n]))
