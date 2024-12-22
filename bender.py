import subprocess, requests, json, sys, os, re

path = os.path.dirname(os.path.realpath(__file__))

asn = sys.argv[1]
gw = sys.argv[2]

def cmd(cmd):
    p = subprocess.run(cmd, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    return [p.stdout.decode('utf-8'),p.stderr.decode('utf-8')]

with open("/etc/iproute2/rt_tables", 'r') as file: rt_tables =  file.read()
if not "ASN" in rt_tables:
    with open("/etc/iproute2/rt_tables", "a") as tables: tables.write("330 ASN\n")

route = cmd("ip rule list table ASN all")[0]
if not "ASN" in route: cmd('ip rule add from 0.0.0.0/0 table ASN')

if not os.path.isfile(f"{path}/allocation.json"): 
    allocation = {}
    with open(f"{path}/allocation.json", 'w') as f: json.dump(allocation, f, indent=4)

with open(f"{path}/allocation.json") as handle: allocation = json.loads(handle.read())

usedIDs = list(allocation.values()) if allocation else []
if not asn in allocation:
    for freeID in range(200, 250):
        if freeID not in usedIDs:
            print(f"Allocated id {freeID} for {asn}")
            allocation[asn] = currentID = freeID
            with open(f"{path}/allocation.json", 'w') as f: json.dump(allocation, f, indent=4)
            break
else:
    currentID = allocation[asn]

if not os.path.isfile(f"{path}/cache/{asn}.txt"):
    request = requests.get(f"https://raw.githubusercontent.com/ipverse/asn-ip/refs/heads/master/as/{asn}/ipv4-aggregated.txt", timeout=(5,5))
    if request.status_code != 200: exit(f"Unable to fetch ips for {asn}")
    with open(f"{path}/cache/{asn}.txt", 'w') as file: file.write(request.text)

with open(f"{path}/cache/{asn}.txt", 'r') as file: ipList =  file.read()
for line in ipList.splitlines():
    if "#" in line: continue
    cmd(f'ip route add {line} via {gw} dev vxlan1 table ASN')