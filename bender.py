import subprocess, requests, json, sys, os, re

path = os.path.dirname(os.path.realpath(__file__))

asn = sys.argv[1]
gw = sys.argv[2]
clear = True if len(sys.argv) > 3 else False

def cmd(cmd):
    p = subprocess.run(cmd, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    return [p.stdout.decode('utf-8'),p.stderr.decode('utf-8')]

with open("/etc/iproute2/rt_tables", 'r') as file: rt_tables =  file.read()
if not "ASN" in rt_tables:
    with open("/etc/iproute2/rt_tables", "a") as tables: tables.write("330 ASN\n")

route = cmd("ip rule list table ASN all")[0]
if not "ASN" in route: cmd('ip rule add from 0.0.0.0/0 table ASN')

if not os.path.isfile(f"{path}/cache/{asn}.txt"):
    request = requests.get(f"https://raw.githubusercontent.com/ipverse/asn-ip/refs/heads/master/as/{asn}/ipv4-aggregated.txt", timeout=(5,5))
    if request.status_code != 200: exit(f"Unable to fetch ips for {asn}")
    with open(f"{path}/cache/{asn}.txt", 'w') as file: file.write(request.text)

with open(f"{path}/cache/{asn}.txt", 'r') as file: ipList =  file.read()
print(f"Removing {len(ipList.splitlines())} routes") if clear else print(f"Applying {len(ipList.splitlines())} routes")
for line in ipList.splitlines():
    if "#" in line: continue
    if clear:
        cmd(f'ip route del {line} via {gw} dev vxlan1 table ASN')
    else:
        cmd(f'ip route add {line} via {gw} dev vxlan1 table ASN')