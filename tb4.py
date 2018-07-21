import requests
import winsound
import pprint

from decimal import *
import logging
failure_multiplier = 1

global logger

logging.basicConfig(
    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.FileHandler("{0}/{1}.log".format(".", "tb4.log")) #,
        #logging.StreamHandler()
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
    global failure_multiplier
    market_ids = []
    resulting_orders = []


    for coin1, coin2 in pairs:
        market_ids.append(find_market_id(coin1, coin2)[0])

    logger.debug("-----------------------------------------------------------------------] Beggining order assembly...")
    logger.debug(
        "[..] Querying total of %s markets: (%s) [Max Orders: %s]" % (
            len(market_ids), ", ".join(str(x) for x in market_ids), max_orders))

    orders = s.get(
        "https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s/%s" % (
            "-".join(str(x) for x in market_ids), max_orders)).json()

    failure_multiplier = Decimal(1)

    while True:
        quantity = initial_quantity
        logger.debug(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> BEGIN OF ORDER")
        try:
            resulting_orders = []
            for coin1, coin2 in pairs:
                if len(resulting_orders) == 0:
                    actual_quantity = Decimal(quantity) * Decimal(failure_multiplier)
                else:
                    actual_quantity = quantity
                suborder = assemble_suborder(coin1, coin2, actual_quantity, orders)
                suborder_price = sum(Decimal(row[2]) for row in suborder)
                suborder_volume = sum(Decimal(row[3]) for row in suborder)

                if suborder[0][1] == "Sell":
                    logger.debug(
                        "[..{4}..] FINAL SUBORDER is {0:.20g} {1} -> {2:.20g} {3}".format(suborder_price, coin1,
                                                                                       suborder_volume,
                                                                                       coin2,
                                                                                       len(resulting_orders)))
                    quantity = suborder_volume

                else:
                    logger.debug(
                        "[....] FINAL SUBORDER is {2:.20g} {1} -> {0:.20g} {3}".format(suborder_price, coin1,
                                                                                       suborder_volume,
                                                                                       coin2))
                    quantity = suborder_price
                resulting_orders += suborder

        except ValueError:
            logger.info("Increasing initial amount.... %s" % failure_multiplier)
            continue
        break


    return ({"Profit": Decimal(quantity) - Decimal(initial_quantity),
             "Orders": resulting_orders})


def assemble_suborder(coin1, coin2, quantity, orders):
    global failure_multiplier
    logger.debug("[....] Starting suborder assembly: %s %s -> %s " % (quantity, coin1, coin2))
    market_id, reversed_market = find_market_id(coin1, coin2)

    for market in orders["Data"]:
        if market["TradePairId"] == market_id:

            resulting_suborders = []
            suborder_price = Decimal(0)
            suborder_volume = Decimal(0)

            for item in trade_pairs:
                if market_id == item["Id"]:
                    market_MinimumBaseTrade = Decimal(item["MinimumBaseTrade"])
                    market_TradeFee = Decimal(item["TradeFee"])

            logger.debug(
                "[....] TradePairId is {0} [MiniminumBaseTrade {1:.20g}]".format(market_id, market_MinimumBaseTrade))

            if reversed_market:
                direction = "Sell"
                if quantity < market_MinimumBaseTrade:
                    logger.error("ORDER TOO SMALL!")
                    logger.error("Current multiplier is %s" % failure_multiplier)
                    failure_multiplier += market_MinimumBaseTrade/quantity
                    logger.error("Increased multiplier is %s" % failure_multiplier)
                    raise ValueError('OrderTooSmall')

                volume_trade_fee = 1
                price_trade_fee = 1 + (market_TradeFee / 100)
            else:
                direction = "Buy"
                # if quantity < 1/market_MinimumBaseTrade:
                #    raise Exception('Order too low')
                price_trade_fee = 1
                volume_trade_fee = 1 - (market_TradeFee / 100)

            while ((suborder_price < quantity and direction == "Sell") or
                   (suborder_volume < quantity and direction == "Buy")) and \
                    len(resulting_suborders) < max_orders and \
                    len(resulting_suborders) < len(market[direction]):

                logger.debug(
                    "[. {5} .] Current suborder [{0:.20g}]: Total Price: {1:.20g} -  Total Volume: {2:.20g} - Total Requested: {3:.20g} {4}".format(
                        len(resulting_suborders) + 1,
                        suborder_price,
                        suborder_volume,
                        quantity,
                        coin1,
                        direction))

                current_volume = Decimal(market[direction][len(resulting_suborders)]["Volume"]) * volume_trade_fee
                current_price = Decimal(market[direction][len(resulting_suborders)]["Total"]) * price_trade_fee

                if (suborder_volume + current_volume <= quantity and direction == "Buy") or \
                        (suborder_price + current_price <= quantity and direction == "Sell"):
                    logger.debug(
                        "[........] Adding WHOLE order: {0:.20g} -> {1:.20g} (Unit price: {2:.20g})".format(
                            current_price,
                            current_volume,
                            market[direction][
                                len(
                                    resulting_suborders)][
                                "Price"]))
                    order_filling_ratio = 1
                else:
                    if direction == "Sell":
                        missing_price = Decimal(quantity) - Decimal(suborder_price)
                        if missing_price < market_MinimumBaseTrade:
                            missing_price = market_MinimumBaseTrade

                        order_filling_ratio = missing_price / current_price
                    else:
                        missing_volume = quantity - suborder_volume
                        # if missing_volume <  (market_MinimumBaseTrade:
                        #    missing_volume = 1 / market_MinimumBaseTrade

                        order_filling_ratio = missing_volume / current_volume

                    logger.debug(
                        "[........] Adding PARTIAL ({0:.3}%) order: {1:.20g} -> {2:.20g} (Unit price: {3:.20g})".format(
                            order_filling_ratio * 100,
                            current_price * order_filling_ratio,
                            current_volume * order_filling_ratio,
                            Decimal(market[
                                      direction][
                                      len(
                                          resulting_suborders)][
                                      "Price"])))

                resulting_suborders.append(
                    [market_id, direction, current_price * order_filling_ratio, current_volume * order_filling_ratio])

                suborder_price += current_price * order_filling_ratio
                suborder_volume += current_volume * order_filling_ratio

            return resulting_suborders


def find_common_minimum(*coins):
    return True


minimum_order = {"BTC": 0.0005,
                 "LTC": 0.01,
                 "DOGE": 10000,
                 "USDT": 1,
                 "NZDT": 1}

global s
s = requests.Session()
coin_pairs = find_market_pairs()
max_orders = 50

while True:
    for coin, markets in coin_pairs.iteritems():
        logging.info("Coin %s has %s available markets: (%s)" % (coin, len(markets), ", ".join(markets)))

        for initial_market in markets:
            for intermediary_market in markets:
                if initial_market != intermediary_market and \
                        initial_market != coin and \
                        intermediary_market != coin:
                    logging.info(" .. Simulating %s>%s, %s>%s, %s>%s" % (
                        initial_market, coin, coin, intermediary_market, intermediary_market, initial_market))

                    trade = assemble_order_quotation(minimum_order[initial_market], [initial_market, coin],
                                                     [coin, intermediary_market], [intermediary_market, initial_market])

                    if trade["Profit"] > 0:
                        print trade
