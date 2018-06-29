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
        if markets["Market"] == "%s_%s" % (coin1, coin2):
            #print "Direction is Sell"
            while order_grand_volume < quantity and qtd_orders < max_orders:
                order_grand_volume += markets["Sell"][qtd_orders]["Volume"]
                order_grand_price += markets["Sell"][qtd_orders]["Total"]
                qtd_orders += 1

        if markets["Market"] == "%s_%s" % (coin2, coin1):
            #print "Direction is Buy"
            while order_grand_volume < quantity and qtd_orders < max_orders:
                order_grand_volume += markets["Buy"][qtd_orders]["Volume"]
                order_grand_price += markets["Buy"][qtd_orders]["Total"]
                qtd_orders += 1
            order_grand_price = (order_grand_price)

    return ([order_grand_volume, order_grand_price, qtd_orders])


# Real thing

max_orders = 1
balances = {'BTC': 1000,
           'LTC': 1000,
           'DOGE': 1000,
           'USDT': 1000,
           'NZDT': 1000}


#--------------

trade_pairs = requests.get("https://www.cryptopia.co.nz/api/GetTradePairs").json()['Data']

coin_pairs = find_market_pairs()

for coin, markets in coin_pairs.iteritems():
    if coin == "GBX":
        print "Coin %s has %s available markets: (%s)" % (coin, len(markets), ', '.join(markets))

        for initial_market in markets:
            for intermediary_market in markets:
                if initial_market != intermediary_market and initial_market != coin and intermediary_market != coin:
                    print " .. Simulating %s>%s, %s>%s, %s>%s" % (
                    initial_market, coin, coin, intermediary_market, intermediary_market, initial_market)

                    a = assemble_order_quotation(initial_market, coin, 1000)
                    print "Step 1 .. %s %s > %s %s" % (a[1], initial_market, a[0], coin)
                    limit = a[1]

                    print "Limit is now %0.10f %s" % (limit, initial_market)

                    b = assemble_order_quotation(coin, intermediary_market, 1000)
                    print "Step 2 .. %s %s > %s %s" % (b[0], coin, b[1], intermediary_market)

                    limit = min(limit, b[1] * (a[1]/a[0]))

                    print "Limit is now %0.10f %s" % (limit, initial_market)

                    c = assemble_order_quotation(intermediary_market, initial_market, 1000)
                    print "Step 3 .. %s %s > %s %s" % (c[1], intermediary_market, c[0], initial_market)

                    limit = min(limit, c[0] * b[1] * (a[1]/a[0]))
                    print "Limit is now %0.10f %s" % (limit, initial_market)



                    print "Capped Step 1 .. %0.8f %s > %0.8f %s" % (limit, initial_market, a[1]/a[0], coin)
                    print "Capped Step 2 .. %0.8f %s > %0.8f %s" % (a[1]/a[0], coin, b[1]* (a[1]/a[0]), intermediary_market)
                    print "       Step 3 .. %0.8f %s > %0.8f %s" % (c[0] / b[1] * (a[1]/a[0]), intermediary_market, c[0] * b[1] * (a[1]/a[0]), initial_market)
