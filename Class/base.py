import subprocess, ipaddress, requests, time, json, re, os
from collections import defaultdict

class Base:

    def __init__(self,path):
        self.path = path

    def call(self,url,max=5):
        allowedCodes, alwaysFetch = [200], ("asn.json","locations.json","version.json")
        for run in range(1,max):
            try:
                path, last =  '/'.join(url.split("/")[3:]), url.split("/")[-1]
                #cache
                if os.path.isfile(f"{self.path}/cache/{path}"):
                    #not older than 1 hour
                    if os.path.getmtime(f"{self.path}/cache/{path}") + (60*60) > int(time.time()):
                        with open(f"{self.path}/cache/{path}") as handle: file =  json.loads(handle.read())
                        return True,file
                    elif not path.endswith(alwaysFetch):
                        versionFile = path.replace(last,"version.json")
                        if os.path.isfile(f"{self.path}/cache/{versionFile}"):
                            with open(f"{self.path}/cache/{versionFile}") as handle: version =  json.loads(handle.read())
                            if version['version'] < os.path.getatime(f"{self.path}/cache/{path}"):
                                with open(f"{self.path}/cache/{path}") as handle: file =  json.loads(handle.read())
                                return True,file
                #download
                os.makedirs(os.path.dirname(f"{self.path}/cache/{path}"), exist_ok=True)
                req = requests.get(url, timeout=(5,5))
                if req.status_code in allowedCodes: 
                    file = req.json()
                    with open(f"{self.path}/cache/{path}", 'w') as f: json.dump(file, f)
                    return True,file
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
        regionIPs = defaultdict(list)
        for subnet, details in routing.items():
            regionIPs[details['location']].append(ipaddress.ip_network(subnet))
        
        aggregated = {}
        for location, ips in regionIPs.items():
            ips.sort()
            aggregated_networks = ipaddress.collapse_addresses(ips)
            aggregated[location] = [str(net) for net in aggregated_networks]
        return aggregated