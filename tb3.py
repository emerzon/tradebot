import requests
#import winsound

def find_market_pairs():
    if 'trade_pairs' not in globals():
        global trade_pairs
        trade_pairs = requests.get("https://www.cryptopia.co.nz/api/GetTradePairs").json()['Data']
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
            return item["Id"], item["MinimumTrade"]


def assemble_order_quotation(coin1, coin2, quantity):

    market_id, market_min_trade = find_market_id(coin1, coin2)
    orders = requests.get("https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s/%s" % (market_id,
                          max_orders)).json()
    for market in orders["Data"]:
        qtd_orders = 0
        order_grand_volume = 0
        order_grand_price = 0
        direction = ""

        if market["Market"] == "%s_%s" % (coin2, coin1):
            direction = "Sell"
        elif market["Market"] == "%s_%s" % (coin1, coin2):
            direction = "Buy"

        if direction != "":
            while ((order_grand_price < quantity and direction == "Sell") or
                   (order_grand_volume < quantity and direction == "Buy")) and \
                    qtd_orders < max_orders and \
                    qtd_orders < len(market[direction]):
                order_grand_volume += market[direction][qtd_orders]["Volume"]
                order_grand_price += market[direction][qtd_orders]["Total"]

                #if order_grand_price > quantity:


                   #print "Requested size %0.12f - Total size %0.12f" % (quantity, order_grand_price)
                   #exceed = order_grand_price - quantity
                   #print "Exceeded %0.12f" % exceed

                   #print "Minimum trade is: %s" % market_min_trade
                   #if exceed > market_min_trade:
                       #print "Last order decrease is possible!"

                       # print "Last order total: %s" % market[direction][qtd_orders]["Total"]
                       # print "Last order volume: %s" % market[direction][qtd_orders]["Volume"]
                       #
                       # last_order_rate = (float(market[direction][qtd_orders]["Volume"]) / float(
                       #     market[direction][qtd_orders]["Total"]))
                       # print "Last order rate: %s" % last_order_rate
                       #
                       # new_order_volume = min(market_min_trade,
                       #                        last_order_rate / (market[direction][qtd_orders]["Volume"] - exceed))
                       #
                       #
                       # new_order_total = (market[direction][qtd_orders]["Total"] - exceed)
                       # print "New last order volume: %s" % new_order_volume
                       # print "New last order total: %s" % new_order_total
                       #
                       # order_grand_price -= market[direction][qtd_orders]["Total"]
                       # order_grand_price += (new_order_total)
                       # order_grand_volume -= market[direction][qtd_orders]["Volume"]
                       # order_grand_volume += (new_order_total * last_order_rate)
                       #
                       # print "Order now is %0.12f" % order_grand_price
                   #else:
                       # print "Last order decrease not possible"

                qtd_orders += 1

            if direction == "Buy":
                order_grand_price *= 1.002

            if direction == "Sell":
                order_grand_price *= 0.998

    return ([order_grand_volume, order_grand_price, qtd_orders])


# Real thing

max_orders = 10
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

fiat = {'BTC': float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/sell").json()['data']['amount']),
        'LTC': float(requests.get("https://api.coinbase.com/v2/prices/LTC-USD/sell").json()['data']['amount'])}

# ----------------------------------------------------------------------------------------------------------------------

coin_pairs = find_market_pairs()

for coin, markets in coin_pairs.iteritems():
    #if coin == "GBX":
    if True:
        print "Coin %s has %s available markets: (%s)" % (coin, len(markets), ', '.join(markets))

        for initial_market in markets:
            for intermediary_market in markets:
                if initial_market != intermediary_market and initial_market != coin and intermediary_market != coin and initial_market not in ['USDT', 'NZDT', 'DOGE'] and intermediary_market not in ['USDT', 'NZDT', 'DOGE']:
                    print " .. Simulating %s>%s, %s>%s, %s>%s" % (
                    initial_market, coin, coin, intermediary_market, intermediary_market, initial_market)

                    a = assemble_order_quotation(initial_market, coin, minimum_order[initial_market])
                    print "Eval 1 .. %0.12f %s > %0.12f %s [%s]" % (a[1], initial_market, a[0], coin, a[2])

                    b = assemble_order_quotation(coin, intermediary_market, a[0])
                    print "Eval 2 .. %0.12f %s > %0.12f %s [%s]" % (b[0], coin, b[1], intermediary_market, b[2])

                    c = assemble_order_quotation(intermediary_market, initial_market, b[1])
                    print "Eval 3 .. %0.12f %s > %0.12f %s [%s]" % (c[0], intermediary_market, c[1], initial_market, c[2])

                    xr_initial_coin = a[0] / a[1]
                    xr_coin_initial = a[1] / a[0]

                    xr_coin_intermediary = b[1] / b[0]
                    xr_intermediary_coin = b[0] / b[1]
                    xr_intermediary_initial = c[0] / c[1]

                    # print " Found exchange rate %s/%s: %0.12f" % (initial_market, coin, xr_initial_coin)
                    # print " Found exchange rate %s/%s: %0.12f" % (coin, initial_market, xr_coin_initial)
                    # print " Found exchange rate %s/%s: %0.12f" % (coin, intermediary_market, xr_coin_intermediary)
                    # print " Found exchange rate %s/%s: %0.12f" % (intermediary_market, coin, xr_intermediary_coin)
                    # print " Found exchange rate %s/%s: %0.12f" % (intermediary_market, initial_market, xr_intermediary_initial)

                    max_for_order_1 = a[1]
                    max_for_order_2 = b[0] * xr_coin_initial
                    max_for_order_3 = c[0] / xr_intermediary_initial

                    # print "Max Orders (%s): %0.12f %0.12f %0.12f" % (initial_market, max_for_order_1, max_for_order_2, max_for_order_3)

                    limit_for_order = min(max_for_order_1, max_for_order_2, max_for_order_3)

                    # print "Will use order size of %0.12f %s" % (limit_for_order, initial_market)

                    amount_1 = limit_for_order
                    amount_2 = limit_for_order / xr_coin_initial
                    amount_3 = amount_2 * xr_coin_intermediary

                    result = amount_3 / xr_intermediary_initial

                    print "Step 1 .. %0.12f %s > %0.12f %s" % (amount_1, initial_market, amount_2, coin)
                    print "Step 2 .. %0.12f %s > %0.12f %s" % (amount_2, coin, amount_3, intermediary_market)
                    print "Step 3 .. %0.12f %s > %0.12f %s" % (amount_3, intermediary_market, result, initial_market)

                    profit = float(result - amount_1)

                    #if True:
                    if profit > 0.000001:
                        winsound.Beep(5500, 100)
                        print "*************************************************************************** Profit %0.12f %s" % (profit, initial_market),
                        if initial_market in fiat.iterkeys():
                            print "( US$ %0.2f )" % (float(fiat[initial_market]) * float(profit))
                        else:
                            print ""
                    else:
                        print "Loss %0.12f %s" % (
                        profit, initial_market),
                        if initial_market in fiat.iterkeys():
                            print "( US$ %0.2f )" % (float(fiat[initial_market]) * float(profit))
                        else:
                            print ""