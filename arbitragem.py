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
cache_bucket_ts = {}
cache_bucket_data = {}


def fetch_fiat(coin):
    if coin in ["BTC", "LTC", "DOGE"]:
            if coin in ["BTC", "LTC"]:
                value = float(dlc("https://api.coinbase.com/v2/prices/%s-USD/sell" % coin)['data']['amount'])
            else:
                value = float(dlc("https://api.cryptowat.ch/markets/kraken/dogebtc/summary")['result']['price']['last']) * fetch_fiat("BTC")
    elif coin in ["USDT"]:
        value = float(0.999)
    else:
        value = 0
    return value


def init_markets():
    global exchanges
    lista = []

    # TradeOgre
    TradeOgre_markets = dlc("https://tradeogre.com/api/v1/markets")
    Cryptopia_markets = dlc("https://www.cryptopia.co.nz/api/GetTradePairs")["Data"]
    Poloniex_markets = dlc("https://poloniex.com/public?command=returnTicker")
    LiquiIO_markets = dlc("https://api.liqui.io/api/3/info")


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

    lista = []
    for k, v in LiquiIO_markets["pairs"].iteritems():
        lista.append("%s-%s" % (k.split("_")[1].upper(), k.split("_")[0].upper()))
    exchanges["LiquiIO"] = lista

def get_values(exchange, market):
    if exchange == "TradeOgre":
        tmp_value = dlc("https://tradeogre.com/api/v1/ticker/%s" % market)
        return ({"Sell": str(tmp_value["ask"]),
                 "Buy": str(tmp_value["bid"])})
    elif exchange == "Cryptopia":
        param = market.split("-")[1] + "_" + market.split("-")[0]
        tmp_value = dlc("https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s/1" % param)
        if len(tmp_value) > 0:
            return ({"Sell": str(tmp_value['Data'][0]['Sell'][0]['Price']),
                     "Buy": str(tmp_value['Data'][0]['Buy'][0]['Price'])})
        else:
            return None
    elif exchange == "Poloniex":
        param = market.split("-")[0] + "_" + market.split("-")[1]
        tmp_value = dlc("https://poloniex.com/public?command=returnTicker")
        return ({"Sell": str(tmp_value[param]["lowestAsk"]),
                 "Buy": str(tmp_value[param]["highestBid"])})
    elif exchange == "LiquiIO":
        param = market.split("-")[1].lower() + "_" + market.split("-")[0].lower()
        tmp_value = dlc("https://api.liqui.io/api/3/ticker/%s" % param)
        return ({"Sell": str(tmp_value[param]["sell"]),
                 "Buy": str(tmp_value[param]["buy"])})


def dlc(url, **kwargs):
    timeout = kwargs.get('timeout')
    global cache_bucket_data
    global cache_bucket_ts
    global s

    url_last_check = cache_bucket_ts.get(url, datetime.datetime(1970, 1, 1))
    if (datetime.datetime.now() - url_last_check).total_seconds() > timeout:
        cache_bucket_data[url] = s.get(url).json()
        cache_bucket_ts[url] = url_last_check

    return cache_bucket_data[url]


init_markets()

while True:

    for xc1 in exchanges:
        for xc2 in exchanges:
            if xc1 != xc2 and xc1 < xc2:
                print "Comparing %s with %s" % (xc1, xc2)
                common_mkt = list(set(exchanges[xc1]).intersection(exchanges[xc2]))
                print "...%s common markets" % len(common_mkt)
                for mkt in common_mkt:
                    #print "Probing %s" % mkt
                    xc1_offer = get_values(xc1, mkt)
                    xc1_buy = float(xc1_offer["Buy"])
                    xc1_sell = float(xc1_offer["Sell"])
                    xc2_offer = get_values(xc2, mkt)
                    xc2_buy = float(xc2_offer["Buy"])
                    xc2_sell = float(xc2_offer["Sell"])
#                    print "[ %.2f%% ][ %.2f ] - [ %.2f ][ %.2f ]" % (xc1_buy, xc1_sell, xc2_buy, xc2_sell)
                    if xc2_sell < xc1_buy and xc2_sell > 0 and xc1_buy >0:
                        print "=== %s [ %s %.2f%% ] === Buy in %s for %.8f and sell in %s for %.8f!" % (
                            time.strftime("%Y-%m-%d %H:%M"), mkt, (xc1_buy / xc2_sell * 100 - 100), xc2, xc2_sell,
                            xc1, xc1_buy)

                    if xc1_sell < xc2_buy and xc1_sell > 0 and xc2_buy >0:
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
