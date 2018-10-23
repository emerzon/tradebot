import requests

btc_value = float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/sell").json()['data']['amount'])
ltc_value = float(requests.get("https://api.coinbase.com/v2/prices/LTC-USD/sell").json()['data']['amount'])

coin = "PIVX"
amount = 1

temp = requests.get("https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s_BTC-%s_LTC/1" % (coin, coin)).json()

print "--- [ Cryptopia BTC ] ---"
print "+ ", temp['Data'][0]['Sell'][0]['Price'], float(temp['Data'][0]['Sell'][0]['Price']) * btc_value * amount
print "- ", temp['Data'][0]['Buy'][0]['Price'], float(temp['Data'][0]['Buy'][0]['Price']) * btc_value * amount

print "--- [ Cryptopia LTC ] ---"
print "+ ", temp['Data'][1]['Sell'][0]['Price'], float(temp['Data'][1]['Sell'][0]['Price']) * ltc_value * amount
print "- ", temp['Data'][1]['Buy'][0]['Price'], float(temp['Data'][1]['Buy'][0]['Price']) * ltc_value * amount

to = requests.get("https://tradeogre.com/api/v1/ticker/BTC-%s" % coin).json()

print "--- TradeOgre BTC --"
print "+ ", to["ask"], float(to["ask"]) * btc_value * amount
print "- ", to["bid"], float(to["bid"]) * btc_value * amount




