#!/usr/bin/env python3
import urllib.request
import json

url = 'https://api.coindesk.com/v1/bpi/currentprice/BTC.json'
response = urllib.request.urlopen(url)
data = json.loads(response.read())

print('Current Bitcoin Price:', data['bpi']['USD']['rate'])