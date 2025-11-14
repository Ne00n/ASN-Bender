# ASN-Bender
Addon for: https://github.com/Ne00n/wg-mesh<br>

![gif](https://i.pinimg.com/originals/ca/67/4d/ca674dde584640c77b55bcbd197575bb.gif)

**Use case**<br>
Lets say you have your own VPN Network, e.g 172.16.5.0/24.<br>
And you want to tunnel, selectively, game traffic over it.

For example, TF2 or CS2, which is the ASN 32590 for Valve.<br>
Traffic via Frankfurt goes via your Frankfurt PoP, Amsterdam via Amsterdam node etc.

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
Any traffic, will look up the routing rules provided by the table ASN.
Which is used by the ASN-Bender.

**Usage**<br>

```
python3 bender.py
python3 bender.py clear
```