import requests
import pprint


def find_market_pairs():
    pairs = {}
    for coin in trade_pairs:
        markets = []
        if coin['Status'] == "OK":
            for base in trade_pairs:
                if coin["Symbol"] == base["Symbol"]:
                    markets.append(base["BaseSymbol"])
        pairs.update({coin["Symbol"]: markets})
    return pairs


def find_market_id(coin1, coin2):
    for item in trade_pairs:
        if item["Label"] == "%s/%s" % (coin1, coin2) or item["Label"] == "%s/%s" % (coin2, coin1):
            return item["Id"]


def assemble_order_quotation(coin1, coin2, quantity):
    orders = requests.get("https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s/%s" % (find_market_id(coin1, coin2),
                          max_orders)).json()
    for markets in orders["Data"]:
        qtd_orders = 0
        order_grand_volume = 0
        order_grand_price = 0
        direction = ""

        if markets["Market"] == "%s_%s" % (coin1, coin2):
            direction = "Sell"
        elif markets["Market"] == "%s_%s" % (coin2, coin1):
            direction = "Buy"

        if direction != "":
            while order_grand_price < quantity and qtd_orders < max_orders:
                order_grand_volume += markets[direction][qtd_orders]["Volume"]
                order_grand_price += markets[direction][qtd_orders]["Total"]
                qtd_orders += 1

    return ([order_grand_volume, order_grand_price, qtd_orders])


# Real thing

max_orders = 40
balances = {'BTC': 1000,
           'LTC': 1000,
           'DOGE': 1000,
           'USDT': 1000,
           'NZDT': 1000}

minimum_order = {'BTC': 0.005,
                 'LTC': 0.01,
                 'DOGE': 100,
                 'USDT': 1,
                 'NZDT': 1}

#--------------

trade_pairs = requests.get("https://www.cryptopia.co.nz/api/GetTradePairs").json()['Data']

coin_pairs = find_market_pairs()

for coin, markets in coin_pairs.iteritems():
    if coin == "GBX":
    #if True:
        print "Coin %s has %s available markets: (%s)" % (coin, len(markets), ', '.join(markets))

        for initial_market in markets:
            for intermediary_market in markets:
                if initial_market != intermediary_market and initial_market != coin and intermediary_market != coin and initial_market != "DOGE" and intermediary_market != "DOGE":
                    print " .. Simulating %s>%s, %s>%s, %s>%s" % (
                    initial_market, coin, coin, intermediary_market, intermediary_market, initial_market)

                    a = assemble_order_quotation(initial_market, coin, minimum_order[initial_market])
                    print "Eval 1 .. %s %s > %s %s" % (a[1], initial_market, a[0], coin)


                    b = assemble_order_quotation(coin, intermediary_market, a[0])
                    print "Eval 2 .. %s %s > %s %s" % (b[0], coin, b[1], intermediary_market)

                    c = assemble_order_quotation(intermediary_market, initial_market, b[1])
                    print "Eval 3 .. %s %s > %s %s" % (c[0], intermediary_market, c[1], initial_market)

                    xr_initial_coin = a[0] / a[1]
                    xr_coin_initial = a[1] / a[0]

                    xr_coin_intermediary = b[1] / b[0]
                    xr_intermediary_coin = b[0] / b[1]
                    xr_intermediary_initial = (1/xr_initial_coin) * xr_intermediary_coin

                    print "Found exchange rate %s/%s: %0.10f" % (initial_market, coin, xr_initial_coin)
                    print "Found exchange rate %s/%s: %0.10f" % (coin, initial_market, xr_coin_initial)
                    print "Found exchange rate %s/%s: %0.10f" % (coin, intermediary_market, xr_coin_intermediary)
                    print "Found exchange rate %s/%s: %0.10f" % (intermediary_market, coin, xr_intermediary_coin)
                    print "Found exchange rate %s/%s: %0.10f" % (intermediary_market, initial_market, xr_intermediary_initial)

                    max_for_order_1 = a[1]
                    max_for_order_2 = (b[1]*b[0]) * xr_initial_for_order_2
                    max_for_order_3 = (c[1]*c[0]) / max_for_order_2

                    print "Max Orders (%s): %0.8f %0.8f %0.8f" % (initial_market, max_for_order_1, max_for_order_2, max_for_order_3)

                    limit_for_order = min(max_for_order_1, max_for_order_2, max_for_order_3)

                    print "Will use order size of %0.8f %s" % (limit_for_order, initial_market)

                    #limit_for_order_1 = a[1]
                    #limit_for_order_2 = b[0] * (a[0] / a[1]) * 0.998
                    #limit_for_order_3 = c[0] * (a[0] / a[1]) * 0.998


                    amount_1 = limit_for_order
                    amount_2 = limit_for_order / max_for_order_2
                    amount_3 = limit_for_order / max_for_order_3
                    amount_4 = limit_for_order / (1/amount_3)

                    print "Step 1 .. %0.10f %s > %0.10f %s" % (amount_1, initial_market, amount_2, coin)
                    print "Step 2 .. %0.10f %s > %0.10f %s" % (amount_2, coin, amount_3, intermediary_market)
                    print "Step 3 .. %0.10f %s > %0.10f %s" % (amount_3, intermediary_market, amount_4, initial_market)

                    profit = (amount_4 - amount_1)

                    if True:
                    #if profit > 0:
                        print "*********************************** Profit %0.10f %s" % (profit, initial_market)
