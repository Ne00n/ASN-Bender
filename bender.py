from Class.base import Base
import subprocess, requests, json, sys, os, re

clear = False
sys.argv = sys.argv[1:]
for param in sys.argv:
    if param.lower() == "clear": clear = True

tools = Base()
path = os.path.dirname(os.path.realpath(__file__))
with open(f"{path}/config.json") as handle: config =  json.loads(handle.read())

tools = Base()
print("Loading asn.json")
success, req = tools.call("https://routing.serv.app/asn.json")
if not success: exit("Failed to fetch asn.json")

availableASNs = req.json()
for selectedASN in config['asnList']:
    if not selectedASN in availableASNs:
        exit(f"ASN {selectedASN} not listed/found.")

print("Loading locations.json")
success, req = tools.call("https://routing.serv.app/locations.json")
if not success: exit("Failed to fetch locations.json")

availableLocations = req.json()
for region,locations in availableLocations.items():
    for location in locations:
        if not location in config['mapping']: print(f"{location} is not in mapping!")

data = {}
for ASN in config['asnList']:
    print(f"Getting files for AS{ASN}")
    for region,locations in availableLocations.items():
        for location in locations:
            success, req = tools.call(f"https://routing.serv.app/data/{region}/{location}/{ASN}.json")
            if not success: exit(f"Failed to fetch {ASN}.json from {location}")
            if not ASN in data: data[ASN] = {}
            if not location in data[ASN]: data[ASN][location] = req.json()

routing = {}
for asn,regions in data.items():
    for region,payload in regions.items():
        for prefix,subnets in payload.items():
            if "::" in prefix: continue
            for subnet, latency in subnets.items():
                if not "/" in subnet: continue
                avrg = tools.getAvrg(latency)
                if not subnet in routing: routing[subnet] = {"latency":999,"region":""}
                if routing[subnet]['latency'] > avrg:
                    routing[subnet] = {"latency":avrg,"region":region}

#on clear, use latest.json
if clear:
    with open(f"{path}/cache/routing.json") as handle: routing =  json.loads(handle.read())
else:
    with open(f"{path}/cache/routing.json", 'w') as f: json.dump(routing, f)

for subnet, details in routing.items():
    if not details['region'] in config['mapping']:
        print(f"{region} is not in mapping!")
        continue
    gw = config['mapping'][details['region']]
    if clear:
        tools.cmd(f'ip route del {subnet} via {gw} dev vxlan1 table ASN')
    else:
        tools.cmd(f'ip route add {subnet} via {gw} dev vxlan1 table ASN')