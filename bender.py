from concurrent.futures import ThreadPoolExecutor
import subprocess, requests, json, sys, os, re
from functools import partial
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

notMapped = []
for region,locations in availableLocations.items():
    for location in locations:
        if not location in config['mapping']: notMapped.append(location)
if notMapped: print(",".join(notMapped),"are not in mapping!")

asnFiles = []
toLoad = list(set(toLoad))
for asn in toLoad:
    for region,locations in availableLocations.items():
        for location in locations:
            if not location in config['mapping']: continue
            asnFiles.append(f"{config['mirror']}/data/{region}/{location}/{asn}.json")
            if f"{config['mirror']}/data/{region}/{location}/version.json" in asnFiles: continue
            asnFiles.append(f"{config['mirror']}/data/{region}/{location}/version.json")

print("Fetching latency data")
toolCall = partial(tools.call, skipLoading=True)
with ThreadPoolExecutor(max_workers=4) as executor:
    list(tqdm(executor.map(toolCall, asnFiles), total=len(asnFiles)))

routing = {}
print("Loading latency data")
for asn in toLoad:
    if not asn in routing: routing[asn] = {}
    for region,locations in availableLocations.items():
        for location in locations:
            if not location in config['mapping']: continue
            try:
                with open(f"{path}/cache/data/{region}/{location}/{asn}.json") as handle: asnData =  json.loads(handle.read())
                for prefix, row in asnData.items():
                    if "::" in prefix: continue
                    if not "data" in row: continue
                    for subnet, latency in row['data'].items():
                        if not latency: continue
                        if "ignoreSubnets" in config and subnet in config['ignoreSubnets']: continue
                        if row['settings'] and 'any' in row['settings']:
                            for entry in latency:
                                subnet, avrg = f"{'.'.join(subnet.split('.')[:3])}.{entry[0]}/32", float(entry[1])
                                if not subnet in routing[asn]: routing[asn][subnet] = {"latency":999,"location":None,"asn":None}
                                if routing[asn][subnet]['latency'] > avrg:
                                    routing[asn][subnet] = {"latency":avrg,"location":location,"asn":asn}
                        else:
                            avrg = tools.getAvrg(latency)
                            if not subnet in routing[asn]: routing[asn][subnet] = {"latency":999,"location":None,"region":{},"asn":None}
                            if routing[asn][subnet]['latency'] > avrg:
                                currentRegion = routing[asn][subnet]["region"]
                                if not region in currentRegion: currentRegion[region] = avrg
                                routing[asn][subnet] = {"latency":avrg,"location":location,"region":currentRegion,"asn":asn}
                            else:
                                currentRegion = routing[asn][subnet]["region"]
                                if not region in currentRegion: currentRegion[region] = avrg
                                routing[asn][subnet]['region'] = currentRegion
            except Exception as e:
                print(f"Error: {e}")

if "anycast" in config or "ignoreAnycast" in config:
    for asn,data in routing.items():
        for subnet,details in list(data.items()):
            if not "region" in details: continue
            if "NA" in details['region'] and "EU" in details['region']:
                diff = abs(details['region']['EU']-details['region']['NA'])
                if diff < 50 and "ignoreAnycast" in config: 
                    del routing[asn][subnet]
                elif diff < 50 and "anycast" in config:
                    routing[asn][subnet]['location'] = config["anycast"]
            elif "AS" in details['region'] and "EU" in details['region']:
                diff = abs(details['region']['EU']-details['region']['AS'])
                if diff < 50 and "ignoreAnycast" in config: 
                    del routing[asn][subnet]
                elif diff < 50 and "anycast" in config:
                    routing[asn][subnet]['location'] = config["anycast"]

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