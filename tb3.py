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
        if item["Label"] == "%s/%s" %(coin1, coin2) or item["Label"] == "%s/%s" % (coin2, coin1):
            return item["Id"]


trade_pairs = requests.get("https://www.cryptopia.co.nz/api/GetTradePairs").json()['Data']

coin_pairs = find_market_pairs()

for coin, markets in coin_pairs.iteritems():
    print "Coin %s has %s available markets: (%s)" % (coin, len(markets), ', '.join(markets))

    for buying_market in markets:
        for selling_market in markets:
            if buying_market != selling_market and buying_market != coin and selling_market != coin:
                print " .. Simulating %s>%s, %s>%s, %s>%s" % (buying_market, coin, coin, selling_market, selling_market, buying_market)
                markets_to_query = "%s-%s-%s" % (find_market_id(coin, buying_market), find_market_id(coin, selling_market), find_market_id(selling_market, buying_market))
                orders = requests.get("https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s/1" % markets_to_query).json()

                for market in orders["Data"]:
                    print market["Market"]

                    if market["Market"] == "%s_%s" % (buying_market, coin):
                        step1_order_volume = market["Buy"][0]["Volume"]
                    if market["Market"] == "%s_%s" % (coin, buying_market):
                        step1_order_volume = market["Sell"][0]["Volume"]

                    if market["Market"] == "%s_%s" % (coin, selling_market):
                        step2_order_volume = market["Buy"][0]["Volume"]
                    if market["Market"] == "%s_%s" % (selling_market, coin):
                        step2_order_volume = market["Sell"][0]["Volume"]

                    if market["Market"] == "%s_%s" % (selling_market, buying_market):
                        step3_order_volume = market["Sell"][0]["Volume"]
                    if market["Market"] == "%s_%s" % (buying_market, selling_market):
                        step3_order_volume = market["Buy"][0]["Volume"]

                order_size = min(step1_order_volume, step2_order_volume, step3_order_volume)

                print "Order size: %0.8f (%0.8f, %0.8f, %0.8f)" % (order_size, step1_order_volume, step2_order_volume, step3_order_volume)
