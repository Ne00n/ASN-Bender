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
tools.updateMirrors()
with open(f"{path}/config.json") as handle: config =  json.loads(handle.read())

print("Loading asn.json")
success, availableASNs = tools.call(f"{config['mirror']}/asn.json")
if not success: exit("Failed to fetch asn.json")

availableASNList, availableTags = [], []
for availableASN, details in availableASNs.items():
    availableASNList.append(int(availableASN))
    if 'tags' in details: availableTags += details['tags']

toLoad = []
if 0 in config['asnList']: config['asnList'] = availableASNList
for selectedASN in config['asnList']:
    for availableASN in availableASNs:
        if not selectedASN in availableASNList:
            exit(f"ASN {selectedASN} not listed/found.")
    toLoad.append(selectedASN)

for selectedTag in config['asnTags']:
    for asn, details in availableASNs.items():
        if not selectedTag in availableTags:
            exit(f"Tag {selectedTag} not listed/found.")
        elif "tags" in details and selectedTag in details['tags']:
            toLoad.append(int(asn))

print("Loading locations.json")
success, availableLocations = tools.call(f"{config['mirror']}/locations.json")
if not success: exit("Failed to fetch locations.json")

for region,locations in availableLocations.items():
    for location in locations:
        if not location in config['mapping']: print(f"{location} is not in mapping!")

asnFiles = []
toLoad = list(set(toLoad))
for asn in toLoad:
    for region,locations in availableLocations.items():
        for location in locations:
            if not location in config['mapping']: continue
            asnFiles.append(f"{config['mirror']}/data/{region}/{location}/{asn}.json")
            if f"{config['mirror']}/data/{region}/{location}/version.json" in asnFiles: continue
            asnFiles.append(f"{config['mirror']}/data/{region}/{location}/version.json")

print("Loading latency data")
with ThreadPoolExecutor(max_workers=4) as executor:
    list(tqdm(executor.map(tools.call, asnFiles), total=len(asnFiles)))

routing = {}
for asn in toLoad:
    for region,locations in availableLocations.items():
        for location in locations:
            if not location in config['mapping']: continue
            try:
                with open(f"{path}/cache/data/{region}/{location}/{asn}.json") as handle: asnData =  json.loads(handle.read())
                for prefix,subnets in asnData.items():
                    if "::" in prefix: continue
                    settings = {}
                    for subnet, latency in subnets.items():
                        if "ignoreSubnets" in config and subnet in config['ignoreSubnets']: continue
                        if subnet == "settings": settings = latency
                        if not "/" in subnet or not latency: continue
                        if not asn in routing: routing[asn] = {}
                        if settings and 'any' in settings:
                            for entry in latency:
                                subnet, avrg = f"{entry[0]}/32", float(entry[1])
                                if not subnet in routing[asn]: routing[asn][subnet] = {"latency":999,"region":None,"asn":None}
                                if routing[asn][subnet]['latency'] > avrg:
                                    routing[asn][subnet] = {"latency":avrg,"location":location,"asn":asn}
                        else:
                            avrg = tools.getAvrg(latency)
                            if not subnet in routing[asn]: routing[asn][subnet] = {"latency":999,"region":None,"asn":None}
                            if routing[asn][subnet]['latency'] > avrg:
                                routing[asn][subnet] = {"latency":avrg,"location":location,"asn":asn}
            except Exception as e:
                print(f"Failed to load /cache/data/{region}/{location}/{asn}.json")

print("Aggregating routing rules...")
aggregated = tools.aggregate(routing)
#on clear, use latest.json
if clear:
    with open(f"{path}/cache/routing.json") as handle: aggregated =  json.loads(handle.read())
else:
    with open(f"{path}/cache/routing.json", 'w') as f: json.dump(aggregated, f)

print("Applying routing rules...")
for asn, data in aggregated.items():
    asnData = availableASNs[str(asn)]
    for location, subnets in data.items():
        tag = tools.inRules(config,asnData)
        if tag:
            gw = config['mapping'][config['rules'][tag]]
        else:
            gw = config['mapping'][location]
        for subnet in subnets:
            if clear:
                tools.cmd(f'ip route del {subnet} via {gw} dev vxlan1 table ASN')
            else:
                tools.cmd(f'ip route add {subnet} via {gw} dev vxlan1 table ASN')

print("Done")