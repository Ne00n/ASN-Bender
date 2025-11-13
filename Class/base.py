import subprocess, ipaddress, requests, time, re
from collections import defaultdict

class Base:

    def call(self,url,method="GET",payload={},headers={},max=5):
        allowedCodes, crashed = [200], False
        for run in range(1,max):
            try:
                if method == "POST":
                    req = requests.post(url, json=payload, timeout=(5,5))
                elif method == "GET":
                    req = requests.get(url, headers=headers, timeout=(5,5))
                else:
                    req = requests.patch(url, json=payload, timeout=(5,5))
                if req.status_code in allowedCodes: return True,req
                crashed = False
            except Exception as ex:
                crashed = True
                pass
            if run == 4 and not crashed:
                return False,req
            elif run == 4:
                return False,None
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