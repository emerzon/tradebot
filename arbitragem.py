# Imports
import requests
import datetime
import time
from decimal import *

# Opcoes
fiat_ttl = 60

# Variable init
s = requests.Session()

exchanges = {}
cache_bucket = {}


def fetch_fiat(coin):
    if coin in ["BTC", "LTC", "DOGE"]:
            if coin in ["BTC", "LTC"]:
                value = float(dlc("https://api.coinbase.com/v2/prices/%s-USD/sell" % coin, 60)['data']['amount'])
            else:
                value = float(dlc("https://api.cryptowat.ch/markets/kraken/dogebtc/summary", 60)['result']['price']['last']) * fetch_fiat("BTC")
    elif coin in ["USDT"]:
        value = float(0.999)
    else:
        value = 0
    return value


def init_markets():
    global exchanges
    lista = []

    # TradeOgre
    TradeOgre_markets = s.get("https://tradeogre.com/api/v1/markets").json()
    Cryptopia_markets = s.get("https://www.cryptopia.co.nz/api/GetTradePairs", stream=False).json()["Data"]
    Poloniex_markets = s.get("https://poloniex.com/public?command=returnTicker").json()

    for market in TradeOgre_markets:
        for k, v in market.iteritems():
            lista.append(k)
        exchanges["TradeOgre"] = lista

    lista = []
    for market in Cryptopia_markets:
        if market["Status"] == "OK":
            lista.append("%s-%s" % (market["BaseSymbol"], market["Symbol"]))
        exchanges["Cryptopia"] = lista

    lista = []
    for market in Poloniex_markets:
        lista.append("%s-%s" % (market.split("_")[0], market.split("_")[1]))
        exchanges["Poloniex"] = lista


def get_values(exchange, market):
    if exchange == "TradeOgre":
        tmp_value = dlc("https://tradeogre.com/api/v1/ticker/%s" % market, 60)
        return ({"Sell": str(tmp_value["ask"]),
                 "Buy": str(tmp_value["bid"])})
    elif exchange == "Cryptopia":
        param = market.split("-")[1] + "_" + market.split("-")[0]
        tmp_value = dlc("https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s/1" % param, 60)
        if len(tmp_value) > 0:
            return ({"Sell": str(tmp_value['Data'][0]['Sell'][0]['Price']),
                     "Buy": str(tmp_value['Data'][0]['Buy'][0]['Price'])})
        else:
            return None
    elif exchange == "Poloniex":
        param = market.split("-")[0] + "_" + market.split("-")[1]
        tmp_value = dlc("https://poloniex.com/public?command=returnTicker", 60)
        return ({"Sell": str(tmp_value[param]["lowestAsk"]),
                 "Buy": str(tmp_value[param]["highestBid"])})


def dlc(url, timeout):
    global cache_bucket
    last_check = cache_bucket[url]["ts"].get(url, datetime.datetime(1970, 1, 1))
    if (datetime.datetime.now() - last_check).total_seconds() < timeout:
            cache_bucket[url]["data"] = s.get(url).json()
    return cache_bucket[url]["data"]


init_markets()

while True:

    for xc1 in exchanges:
        for xc2 in exchanges:
            if xc1 != xc2 and xc1 < xc2:
                print "Comparing %s with %s" % (xc1, xc2)
                common_mkt = list(set(exchanges[xc1]).intersection(exchanges[xc2]))
                print "...%s common markets" % len(common_mkt)
                for mkt in common_mkt:
  #                  print "Probing %s" % mkt
                    xc1_offer = get_values(xc1, mkt)
                    xc1_buy = float(xc1_offer["Buy"])
                    xc1_sell = float(xc1_offer["Sell"])
                    xc2_offer = get_values(xc2, mkt)
                    xc2_buy = float(xc2_offer["Buy"])
                    xc2_sell = float(xc2_offer["Sell"])
 #                   print "[ %.2f%% ][ %.2f ] - [ %.2f ][ %.2f ]" % (xc1_buy, xc1_sell, xc2_buy, xc2_sell)
                    if xc2_sell < xc1_buy:
                        print "=== %s [ %s %.2f%% ] === Buy in %s for %.8f and sell in %s for %.8f!" % (
                            time.strftime("%Y-%m-%d %H:%M"), mkt, (xc1_buy / xc2_sell * 100 - 100), xc2, xc2_sell,
                            xc1, xc1_buy)

                    if xc1_sell < xc2_buy:
                        print "=== %s [ %s %.2f%% ] === Buy in %s for %.8f and sell in %s for %.8f!" % (
                            time.strftime("%Y-%m-%d %H:%M"), mkt, (xc2_buy / xc1_sell * 100 - 100), xc1, xc1_sell,
                            xc2, xc2_buy)

#                    except:
#                        pass
                    # if xc2_sell <= xc1_buy or xc1_sell <= xc2_buy:
                    #     print mkt
                    #     print " %s: " % xc1
                    #     print "  (-) : %.8f - US$ %.8f" % (xc1_buy, xc1_buy * fetch_fiat(mkt.split("-")[0]))
                    #     print "  (+) : %.8f - US$ %.8f" % (xc1_sell, xc1_sell * fetch_fiat(mkt.split("-")[0]))
                    #     print " %s: " % xc2
                    #     print "  (-) : %.8f - US$ %.8f" % (xc2_buy, xc2_buy * fetch_fiat(mkt.split("-")[0]))
                    #     print "  (+) : %.8f - US$ %.8f" % (xc2_sell, xc2_sell * fetch_fiat(mkt.split("-")[0]))

    print "------------------------------------------------------------------"
    time.sleep(30)
