import subprocess, ipaddress, requests, time, json, re, os
from collections import defaultdict

class Base:

    def __init__(self,path):
        self.path = path

    def call(self,url,max=5):
        allowedCodes = [200]
        for run in range(1,max):
            try:
                path =  '/'.join(url.split("/")[3:])
                os.makedirs(os.path.dirname(f"{self.path}/cache/{path}"), exist_ok=True)
                if os.path.isfile(f"{self.path}/cache/{path}") and os.path.getmtime(f"{self.path}/cache/{path}") + (60*60) > int(time.time()):
                    with open(f"{self.path}/cache/{path}") as handle: file =  json.loads(handle.read())
                    return True,file
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
            regionIPs[details['region']].append(ipaddress.ip_network(subnet))
        
        aggregated = {}
        for region, ips in regionIPs.items():
            ips.sort()
            aggregated_networks = ipaddress.collapse_addresses(ips)
            aggregated[region] = [str(net) for net in aggregated_networks]
        return aggregated