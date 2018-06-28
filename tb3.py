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


trade_pairs = requests.get("https://www.cryptopia.co.nz/api/GetTradePairs").json()['Data']

coin_pairs = find_market_pairs()

for coin, markets in coin_pairs.iteritems():
    print "Coin %s has %s available markets: (%s)" % (coin, len(markets), ', '.join(markets))

    for buying_market in markets:
        for selling_market in markets:
            if buying_market != selling_market and coin != buying_market and coin != selling_market:
                if "%s/%s" % (coin, buying_market) in trade_pairs:
                    if "%s/%s" % (coin, selling_market) in trade_pairs:
                        if "%s/%s" % (selling_market, buying_market) in trade_pairs:
                            print " .. Simulating %s<%s, %s>%s, %s>%s" % (coin, buying_market, coin, selling_market, selling_market, buying_market)

                            markets_to_query = "%s_%s-%s_%s-%s_%s" % (coin, buying_market, coin, selling_market, selling_market, buying_market)

                            orders = requests.get(
                                "https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s/1" % markets_to_query).json()

                            for market in orders["Data"]:
                                print market["Market"]
                            #if market["Market"] == "%s_%s" % (buying_market, coin):
                            #print item["Data"]
                            #if item["Data"][0]["Market"] ==
                            #    step1_order_volume = item["Buy"][0]["Volume"]
                            #elif item["Market"] == "%s_%s" % (coin, selling_market):
                            #    step2_order_volume = item["Buy"][0]["Volume"]
                            #else:
                            #    step3_order_volume = item["Sell"][0]["Volume"]

                            #order_size = min(step1_order_volume, step2_order_volume, step3_order_volume)

                            #print "Order size: %0.8f (%0.8f, %0.8f, %0.8f)" % (order_size, step1_order_volume, step2_order_volume, step3_order_volume)
