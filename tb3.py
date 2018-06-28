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


trade_pairs = requests.get("https://www.cryptopia.co.nz/api/GetTradePairs").json()['Data']

coin_pairs = find_market_pairs()

for coin, markets in coin_pairs.iteritems():
    if coin =="GBX":
        print "Coin %s has %s available markets: (%s)" % (coin, len(markets), ', '.join(markets))

        for initial_market in markets:
            for intermediary_market in markets:
                if initial_market != intermediary_market and initial_market != coin and intermediary_market != coin:
                    print " .. Simulating %s>%s, %s>%s, %s>%s" % (initial_market, coin, coin, intermediary_market, intermediary_market, initial_market)

                    markets_to_query = "%s-%s-%s" % (
                    find_market_id(coin, initial_market), find_market_id(coin, intermediary_market),
                    find_market_id(intermediary_market, initial_market))
                    orders = requests.get(
                         "https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s/1" % markets_to_query).json()

                    for market in orders["Data"]:
                         print market

                        # Aqui vou comprar, entao valor e SELL
                         if market["Market"] == "%s_%s" % (coin, initial_market):
                            step1_order_volume = float(market["Sell"][0]["Volume"])
                            step1_unit_price = float(market["Sell"][0]["Price"])

                         # Aqui vou vender, valor e BUY
                         if market["Market"] == "%s_%s" % (coin, intermediary_market):
                            step2_order_volume = float(market["Buy"][0]["Volume"])
                            step2_unit_price = float(market["Buy"][0]["Price"])

                         if market["Market"] == "%s_%s" % (intermediary_market, initial_market):
                            step3_order_volume = float(market["Sell"][0]["Volume"])
                            step3_unit_price = float(market["Sell"][0]["Price"])

                    step1_limit = min(step1_order_volume, step2_order_volume)
                    step2_limit = min(step2_order_volume, step3_order_volume)
                    step3_limit = step3_order_volume

                    step1_total = step1_unit_price * step1_limit
                    step2_total = step2_unit_price * step2_limit
                    step3_total = step3_unit_price * step3_limit



                    #print "Order size %0.10f (%0.10f - %0.10f)" % (order_size_1, step1_order_volume, step2_order_volume)

                                        #
                    # order_size_2 = min(order_size_1, step2_order_volume, step3_order_volume)
                    # step2_total = step2_value * order_size_2
                    #
                    # order_size_3 = min(step3_order_volume, step2_order_volume, step3_order_volume)
                    # step3_total = step3_value * order_size_3
                    #
                    print "Step 1 - %0.10f %s > %0.10f %s" % (step1_total, initial_market, step1_order_volume, coin)
                    print "Step 2 - %0.10f %s > %0.10f %s" % (step2_limit, coin, step2_total, intermediary_market)
                    print "Step 3 - %0.10f %s > %0.10f %s" % (step3_total, intermediary_market, step3_order_volume, initial_market)


