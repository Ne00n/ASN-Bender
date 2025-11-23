# ASN-Bender
Addon for: https://github.com/Ne00n/wg-mesh<br>

![gif](https://i.pinimg.com/originals/ca/67/4d/ca674dde584640c77b55bcbd197575bb.gif)

**Use case**<br>
Lets say you have your own VPN Network, e.g 172.16.5.0/24.<br>
And you want to tunnel, selectively, game traffic over it.

For example, TF2 or CS2, which is the ASN 32590 for Valve.<br>
Traffic for Frankfurt goes via your Frankfurt PoP, traffic for Amsterdam via your Amsterdam PoP etc.

**Depdencies**<br>
requests + tqdm (python3-requests python3-tqdm for Debian)<br>

**Setup**<br>

Edit your config.json, add your ASN's and setup the mapping
```
cp config.example.json config.json
```
Add the table "ASN" to /etc/iproute2/rt_tables
```
330 ASN
```
Add a lookup rule
```
ip rule add from 0.0.0.0/0 table ASN
```
Any traffic (0.0.0.0/0), will look up the routing rules provided by the table ASN.<br>

**Usage**<br>

```
python3 bender.py
python3 bender.py clear
```

You can manually verify the applied routes with<br>
```
ip route show table ASN
```

**Config**<br>
<b>asnList</b><br>
Can be empty, contain one or multiple ASN numbers, or 0 for all available ASN's<br>
<b>asnTags</b><br>
Can be empty or contain tags such as "valve", for the Valve AS32590<br>
<b>mapping</b><br>
All fields are mandatory, even if, for example you don't have a server in London.<br>
In this case, map it to Amsterdam or Frankfurt or whatever is geographically close.<br>