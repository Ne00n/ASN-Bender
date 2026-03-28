import subprocess, ipaddress, requests, time, json, re, os
from collections import defaultdict
from urllib.parse import urlparse

class Base:

    def __init__(self,path):
        self.path = path

    def call(self,url,skipLoading=False,max=5):
        alwaysFetch = ("asn.json","locations.json","version.json")
        for run in range(1,max):
            try:
                path, last =  '/'.join(url.split("/")[3:]), url.split("/")[-1]
                #cache
                if os.path.isfile(f"{self.path}/cache/{path}"):
                    #not older than 1 hour
                    if os.path.getmtime(f"{self.path}/cache/{path}") + (60*60) > int(time.time()):
                        if skipLoading: return True,{}
                        with open(f"{self.path}/cache/{path}") as handle: file =  json.loads(handle.read())
                        return True,file
                    elif not path.endswith(alwaysFetch):
                        versionFile = path.replace(last,"version.json")
                        if os.path.isfile(f"{self.path}/cache/{versionFile}"):
                            with open(f"{self.path}/cache/{versionFile}") as handle: version =  json.loads(handle.read())
                            if version['files'][path.split("/")[-1]]['version'] < os.path.getmtime(f"{self.path}/cache/{path}"):
                                if skipLoading: return True,{}
                                with open(f"{self.path}/cache/{path}") as handle: file =  json.loads(handle.read())
                                return True,file
                #download
                os.makedirs(os.path.dirname(f"{self.path}/cache/{path}"), exist_ok=True)
                req = requests.get(url, timeout=(5,5))
                if req.status_code == 200:
                    file = req.json()
                    with open(f"{self.path}/cache/{path}", 'w') as f: json.dump(file, f)
                    if skipLoading: return True,None 
                    return True,file
                elif req.status_code == 404:
                    return False,{}
            except Exception as ex:
                pass
            if run == 4: return False,{}
            time.sleep(2)

    def cmd(self,cmd,timeout=None):
        try:
            p = subprocess.run(cmd, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, timeout=timeout)
            return [p.stdout.decode('utf-8'),p.stderr.decode('utf-8')]
        except:
            return ["",""]

    def getAvrg(self,pings):
        avrg = 0
        for row in pings:
            avrg += float(row[1])
        return round(avrg / len(pings),1)

    def aggregate(self,routing):
        regionIPs, totalSubnets = {}, 0
        for asn, subnets in routing.items():
            totalSubnets += len(subnets)
            for subnet, details in subnets.items():
                if not asn in regionIPs: regionIPs[asn] = {}
                if not details['location'] in regionIPs[asn]: regionIPs[asn][details['location']] = []
                regionIPs[asn][details['location']].append(ipaddress.ip_network(subnet))
        
        aggregated, aggregatedSubnets = {}, 0
        for asn, data in regionIPs.items():
            if not asn in aggregated: aggregated[asn] = {}
            for location, subnets in data.items():
                if not location in aggregated[asn]: aggregated[asn][location] = []
                aggregated[asn][location] = [str(net) for net in ipaddress.collapse_addresses(subnets)]
                aggregatedSubnets += len(aggregated[asn][location])

        print(f"Aggregated {totalSubnets} subnets to {aggregatedSubnets} subnets")
        return aggregated

    def updateMirrors(self):
        mirrors = ["https://routing.serv.app/","https://ch.routing.serv.app/"]
        with open(f"{self.path}/config.json") as handle: config =  json.loads(handle.read())
        if not "mirrors" in config: config['mirrors'] = []
        for mirror in mirrors:
            if not mirror in config['mirrors']: config['mirrors'].append(mirror)
        if not "mirror" in config:
            lowest = {"mirror":"","latency":999}
            print("Choosing closest mirror")
            for mirror in config['mirrors']:
                try:
                    req = requests.get(f"{mirror}/locations.json", timeout=(5,5))
                    if req.status_code != 200: 
                        print(f"Ignoring {mirror}, non 200 status code")
                        continue
                    if float(req.elapsed.total_seconds()) < lowest['latency']:
                        lowest['latency'] = float(req.elapsed.total_seconds())
                        lowest['mirror'] = mirror
                except Exception as e:
                    print(f"Failed to get response time from mirror {mirror}: {e}")
            if not lowest['mirror']: exit("Unable to find closest mirror.")
            print(f"Selected {lowest['mirror']} as mirror")
            config['mirror'] = lowest['mirror']
        with open(f"{self.path}/config.json", 'w') as f: json.dump(config, f, indent=2)

    def batch(self,aggregated,config,availableASNs,clear):
        batch = ""
        for asn, data in aggregated.items():
            asnData = availableASNs[str(asn)]
            for location, subnets in data.items():
                tag = self.inRules(config,asnData)
                if tag:
                    gw = config['mapping'][config['rules'][tag]]
                else:
                    gw = config['mapping'][location]
                for subnet in subnets:
                    batch += f'ip route add {subnet} via {gw} dev vxlan1 table ASN\n'
        with open(f"{self.path}/routing.batch", 'w') as f: f.write(batch)
        self.cmd(f'ip -batch {self.path}/routing.batch')

    def inRules(self,config,asnData):
        for tag in asnData['tags']:
            if tag in config['rules']:
                return tag
