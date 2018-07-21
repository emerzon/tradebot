import requests
import winsound

import logging

global logger
logging.basicConfig(
    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.FileHandler("{0}/{1}.log".format(".", "tb4.log")),
        logging.StreamHandler()
    ],
    level=logging.DEBUG)

logger = logging.getLogger(__name__)

def find_market_pairs():
    if "trade_pairs" not in globals():
        global trade_pairs
        trade_pairs = s.get("https://www.cryptopia.co.nz/api/GetTradePairs", stream=False).json()["Data"]
    pairs = {}
    for coin in trade_pairs:
        markets = []
        if coin["Status"] == "OK":
            for base in trade_pairs:
                if coin["Symbol"] == base["Symbol"]:
                    markets.append(base["BaseSymbol"])
        pairs.update({coin["Symbol"]: markets})
    return pairs


def find_market_id(coin1, coin2):
    for item in trade_pairs:
        if item["Label"] == "%s/%s" % (coin1, coin2) or item["Label"] == "%s/%s" % (coin2, coin1):
            if coin1 == item["BaseSymbol"]:
                reversed_market = True
            else:
                reversed_market = False

            return item["Id"], reversed_market


def assemble_order_quotation(initial_quantity, *pairs):
    quantity = 0
    market_ids = []
    for coin1, coin2 in pairs:
        market_ids.append(find_market_id(coin1, coin2)[0])

    logger.debug(
        "Querying total of %s markets: (%s) [Max Orders: %s]" % (len(market_ids), "-".join(str(x) for x in market_ids), max_orders))
    orders = s.get(
        "https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s/%s" % ("-".join(str(x) for x in market_ids), max_orders)).json()

    print orders

    for coin1, coin2 in pairs:
        if quantity == 0:
            quantity = initial_quantity

        logger.debug("------> Starting order assembly: %s %s -> %s " % (quantity, coin1, coin2))
        market_id, reversed_market = find_market_id(coin1, coin2)

        for market in orders["Data"]:
            if market["TradePairId"] == market_id:
                market_MinimumTrade = trade_pairs[market_id]["MinimumTrade"]
                market_MinimumBaseTrade = trade_pairs[market_id]["MinimumBaseTrade"]
                market_TradeFee = trade_pairs[market_id]["TradeFee"]
                market_BaseSymbol = trade_pairs[market_id]["BaseSymbol"]

                logger.debug("TradePairId is %s [MinimumTrade: %s - MiniminumBaseTrade %s" % (
                market_id, market_MinimumTrade, market_MinimumBaseTrade))

                if reversed_market:
                    direction = "Sell"
                    logger.debug("Sell Order")
                else:
                    direction = "Buy"
                    logger.debug("Sell Order")

                qtd_orders = 0
                order_grand_volume = 0
                order_grand_price = 0

                while ((order_grand_price < quantity and direction == "Sell") or
                       (order_grand_volume < quantity and direction == "Buy")) and \
                        qtd_orders < max_orders and \
                        qtd_orders < len(market[direction]):

                    qtd_orders += 1

                    if order_grand_volume + market[direction][qtd_orders]["Volume"] <= quantity:
                        logger.debug("Adding WHOLE order: %s -> %s (Unit price: %s)" % (
                        market[direction][qtd_orders]["Volume"], market[direction][qtd_orders]["Total"],
                        market[direction][qtd_orders]["Price"]))
                        order_grand_volume += market[direction][qtd_orders]["Volume"]
                        order_grand_price += market[direction][qtd_orders]["Total"]
                    else:
                        logger.debug("Adding PARTIAL order... #TODO")
                        order_grand_volume += market[direction][qtd_orders]["Volume"]
                        order_grand_price += market[direction][qtd_orders]["Total"]

                    if not reversed_market:

                        order_grand_price *= 1 + market_TradeFee
                    else:
                        logger.debug("Sell Order")
                        order_grand_volume *= 1 - market_TradeFee

    return ([order_grand_volume, order_grand_price, qtd_orders])


global s
s = requests.Session()
coin_pairs = find_market_pairs()
max_orders = 10

print assemble_order_quotation(1, ["BTC", "LTC"])
