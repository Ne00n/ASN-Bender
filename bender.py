from concurrent.futures import ThreadPoolExecutor
import subprocess, requests, json, sys, os, re
from Class.base import Base
from tqdm import tqdm

clear = False
sys.argv = sys.argv[1:]
for param in sys.argv:
    if param.lower() == "clear": clear = True

path = os.path.dirname(os.path.realpath(__file__))
tools = Base(path)
with open(f"{path}/config.json") as handle: config =  json.loads(handle.read())

print("Loading asn.json")
success, availableASNs = tools.call("https://routing.serv.app/asn.json")
if not success: exit("Failed to fetch asn.json")

availableASNList = []
for availableASN in availableASNs:
    availableASNList.append(int(availableASN))

if 0 in config['asnList']: config['asnList'] = availableASNList
for selectedASN in config['asnList']:
    for availableASN in availableASNs:
        if not selectedASN in availableASNList:
            exit(f"ASN {selectedASN} not listed/found.")

print("Loading locations.json")
success, availableLocations = tools.call("https://routing.serv.app/locations.json")
if not success: exit("Failed to fetch locations.json")

for region,locations in availableLocations.items():
    for location in locations:
        if not location in config['mapping']: exit(f"{location} is not in mapping!")

asnFiles = []
for ASN in config['asnList']:
    for region,locations in availableLocations.items():
        for location in locations:
            asnFiles.append(f"https://routing.serv.app/data/{region}/{location}/{ASN}.json")
            if f"https://routing.serv.app/data/{region}/{location}/version.json" in asnFiles: continue
            asnFiles.append(f"https://routing.serv.app/data/{region}/{location}/version.json")

print("Loading latency data")
with ThreadPoolExecutor(max_workers=4) as executor:
    list(tqdm(executor.map(tools.call, asnFiles), total=len(asnFiles)))

data = {}
for ASN in config['asnList']:
    for region,locations in availableLocations.items():
        for location in locations:
            with open(f"{path}/cache/data/{region}/{location}/{ASN}.json") as handle: asnData =  json.loads(handle.read())
            if not ASN in data: data[ASN] = {}
            if not location in data[ASN]: data[ASN][location] = asnData

routing = {}
for asn,regions in data.items():
    for region,payload in regions.items():
        for prefix,subnets in payload.items():
            if "::" in prefix: continue
            settings = {}
            for subnet, latency in subnets.items():
                if subnet == "settings": settings = latency
                if not "/" in subnet: continue
                if settings and settings['any']:
                    for entry in latency:
                        subnet, avrg = f"{entry[0]}/32", float(entry[1])
                        if not subnet in routing: routing[subnet] = {"latency":999,"region":""}
                        if routing[subnet]['latency'] > avrg:
                            routing[subnet] = {"latency":avrg,"region":region}
                else:
                    avrg = tools.getAvrg(latency)
                    if not subnet in routing: routing[subnet] = {"latency":999,"region":""}
                    if routing[subnet]['latency'] > avrg:
                        routing[subnet] = {"latency":avrg,"region":region}

aggregated = tools.aggregate(routing)
#on clear, use latest.json
if clear:
    with open(f"{path}/cache/routing.json") as handle: aggregated =  json.loads(handle.read())
else:
    with open(f"{path}/cache/routing.json", 'w') as f: json.dump(aggregated, f)

print("Applying routing rules...")
for region, subnets in aggregated.items():
    gw = config['mapping'][region]
    for subnet in subnets:
        if clear:
            tools.cmd(f'ip route del {subnet} via {gw} dev vxlan1 table ASN')
        else:
            tools.cmd(f'ip route add {subnet} via {gw} dev vxlan1 table ASN')

print("Done")