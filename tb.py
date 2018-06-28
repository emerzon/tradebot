import time
import requests

# print btc_value
# print ltc_value

coin_btc_buy = {}
coin_btc_sell = {}

coin_ltc_buy = {}
coin_ltc_sell = {}

coins = []
ltc_coins = []
btc_coins = []

for pair in requests.get("https://www.cryptopia.co.nz/api/GetTradePairs").json()['Data']:
    if pair["BaseSymbol"] in ["LTC"]:
        ltc_coins.append(pair["Symbol"])
    elif pair["BaseSymbol"] in ["BTC"]:
        btc_coins.append(pair["Symbol"])

for coin in btc_coins:
    if coin in ltc_coins:
        coins.append(coin)

refresh_fiat_values_loop = 10

while True:

    if refresh_fiat_values_loop == 10:
        print "Refreshing fiat values"
        btc_value = float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/sell").json()['data']['amount'])
        ltc_value = float(requests.get("https://api.coinbase.com/v2/prices/LTC-USD/sell").json()['data']['amount'])
        refresh_fiat_values_loop = 0

    print refresh_fiat_values_loop

    for coin in coins:
        #print '[%s]' % coin,
        temp = requests.get(
            "https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s_BTC-%s_LTC/1" % (coin, coin)).json()
        try:
            coin_btc_buy.update({coin: float(temp['Data'][0]['Buy'][0]['Price'])})
            coin_btc_sell.update({coin: float(temp['Data'][0]['Sell'][0]['Price'])})
            btc_buy_order_size = float(temp['Data'][0]['Buy'][0]['Volume'])
            btc_sell_order_size = float(temp['Data'][0]['Sell'][0]['Volume'])
            coin_ltc_buy.update({coin: float(temp['Data'][1]['Buy'][0]['Price'])})
            coin_ltc_sell.update({coin: float(temp['Data'][1]['Sell'][0]['Price'])})
            ltc_buy_order_size = float(temp['Data'][1]['Buy'][0]['Volume'])
            ltc_sell_order_size = float(temp['Data'][1]['Sell'][0]['Volume'])
        except:
            coin_btc_buy.update({coin: 0})
            coin_btc_sell.update({coin: 0})
            btc_buy_order_size = 0
            btc_sell_order_size = 0
            coin_ltc_buy.update({coin: 0})
            coin_ltc_sell.update({coin: 0})
            ltc_buy_order_size = 0
            ltc_sell_order_size = 0

        # ltc_temp = requests.get("https://www.cryptopia.co.nz/api/GetMarketOrders/%s_LTC/1" % coin).json()

        # print "%s - BTC B%s - S%s (~%s)" % (coin, coin_btc_buy[coin] * btc_value, coin_btc_sell[coin] * btc_value
        #                                             coin_btc_sell[coin] / coin_btc_buy[coin] * 100 - 100)
        # print "%s - LTC B%s - S%s (~%s)" % (coin, coin_ltc_buy[coin] * ltc_value, coin_ltc_sell[coin] * ltc_value,
        # coin_ltc_sell[coin] / coin_ltc_buy[coin] * 100 - 100)

        if coin_btc_sell[coin] * 1.002 * btc_value < coin_ltc_buy[coin] * 0.998 * ltc_value:
            order_size = float(min(btc_sell_order_size, ltc_buy_order_size))
            buying_cost = (order_size * coin_btc_sell[coin]) * 1.002
            selling_value = (order_size * coin_ltc_buy[coin]) * 0.998
            gain = selling_value * ltc_value - buying_cost * btc_value

            if buying_cost >= 0.0005:
                print
                print "-------- [%s] -------" % coin
                print "Considering BTC>LTC: (%0.8f)>(%0.8f) " % (btc_sell_order_size, ltc_buy_order_size)
                print "BUY:  %0.8f Units - Rate: %0.8f - Total %0.8f BTC (US$ %0.8f)" % (
                order_size, (coin_btc_sell[coin]), buying_cost, buying_cost * btc_value)
                print "SELL: %0.8f Units - Rate: %0.8f - Total %0.8f LTC (US$ %0.8f)" % (
                order_size, (coin_ltc_buy[coin]), selling_value, selling_value * ltc_value)
                print "NET gain is US$ %0.8f" % gain

        if coin_ltc_sell[coin] < coin_btc_buy[coin]:
            print "Considering LTC(%s)>BTC(%s)" % (ltc_sell_order_size, btc_buy_order_size)
            order_size = min(ltc_sell_order_size, btc_buy_order_size)
            print "Order size will be %s " % order_size
            print "Buying cost is %s" % (order_size * coin_ltc_sell[coin])
            print "Selling value is %s " % (order_size * coin_btc_sell[coin])

        # else:
        #   print "Not considering trade now"

    refresh_fiat_values_loop += 1
    time.sleep(1)
