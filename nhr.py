import json
import requests


current_profitability = requests.get("https://api.nicehash.com/api?method=stats.global.current").json()

for algo in current_profitability["result"]["stats"]:
    print algo
