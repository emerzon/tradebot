import requests

btc_value = float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/sell").json()['data']['amount'])
ltc_value = float(requests.get("https://api.coinbase.com/v2/prices/LTC-USD/sell").json()['data']['amount'])

coin = "GBX"

temp = requests.get("https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s_BTC-%s_LTC/1" % (coin, coin)).json()

print float(temp['Data'][0]['Sell'][0]['Price']) * btc_value
print float(temp['Data'][1]['Sell'][0]['Price']) * ltc_value