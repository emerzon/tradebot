# Stupid imports
import requests
from tabulate import tabulate
import winsound
import pprint
import cryptopia_api
from decimal import *
import logging
import datetime

# Init settings
getcontext().prec = 15
fiat_ttl = 10

# Variable inits
failure_multiplier = Decimal(1)
s = requests.Session()
fiat_values = {}
fiat_lastcheck = {}

minimum_order = {"BTC": Decimal(0.0005 * 1.002),
                 "LTC": Decimal(0.048 * 1.002),
                 "DOGE": Decimal(100 * 1.002),
                 "USDT": Decimal(5 * 1.002),
                 "NZDT": Decimal(1 * 1.002)}

max_orders = 50

# Logger settings
logging.basicConfig(
    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.FileHandler("{0}/{1}.log".format(".", "tb4.log"))  # ,
        # logging.StreamHandler()
    ],
    level=logging.DEBUG)

logger = logging.getLogger(__name__)


# Functions Begin here
# ----------------------------------------------------------------------------------------------------------------------

def fetch_fiat(coin):
    global fiat_values
    global fiat_lastcheck


    if coin in ["BTC", "LTC"]:
        last_check = fiat_lastcheck.get(coin, datetime.datetime(1970, 1, 1))


        if (datetime.datetime.now() - last_check).total_seconds() > fiat_ttl:
            value = Decimal(requests.get("https://api.coinbase.com/v2/prices/%s-USD/sell" % coin).json()['data']['amount'])
            fiat_values[coin] = value
            fiat_lastcheck[coin] = datetime.datetime.now()

        return fiat_values[coin]

    elif coin in ["USDT"]:
        return 1
    else:
        return 0


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

    for coin1, coin2 in pairs:
        market_ids.append(find_market_id(coin1, coin2)[0])

    logger.debug("[..] Beggining order assembly...")
    logger.debug(
        "[..] Querying total of %s markets: (%s) [Max Orders: %s]" % (
            len(market_ids), ", ".join(str(x) for x in market_ids), max_orders))

    orders = s.get(
        "https://www.cryptopia.co.nz/api/GetMarketOrderGroups/%s/%s" % (
            "-".join(str(x) for x in market_ids), max_orders)).json()

    failure_multiplier = Decimal(1)

    for i in range(0, 300):
        if i == 100:
            raise OverflowError("Deu merda")
        quantity = initial_quantity
        try:
            resulting_orders = []
            for coin1, coin2 in pairs:
                if len(resulting_orders) == 0:
                    actual_quantity = Decimal(quantity) * Decimal(failure_multiplier)
                else:
                    actual_quantity = Decimal(quantity)
                suborder = assemble_suborder(coin1, coin2, actual_quantity, orders)

                if len(suborder) == 0:
                    raise OverflowError('Empty market!')

                suborder_price = Decimal(sum(Decimal(row[2]) for row in suborder))
                suborder_volume = Decimal(sum(Decimal(row[3]) for row in suborder))

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

    return (resulting_orders)


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
                    market_TradeFee = Decimal(item["TradeFee"])
                    market_MinimumBaseTrade = Decimal(item["MinimumBaseTrade"]) * 1 + (market_TradeFee / 100)
                    market_BaseSymbol = item["BaseSymbol"]

            logger.debug(
                "[....] TradePairId is {0} [MiniminumBaseTrade {1:.20g}]".format(market_id, market_MinimumBaseTrade))

            if reversed_market:
                direction = "Sell"
                actual_coin1 = coin1
                actual_coin2 = coin2
                trade_fee = Decimal(1 + (market_TradeFee / 100))

                # if quantity < market_MinimumBaseTrade:
                #     if len(resulting_suborders) >= len(market[direction]):
                #         raise OverflowError("Market too small!")
                #     else:
                #         logger.debug("ORDER TOO SMALL! 1 Market %s Orders %s" % (
                #             len(market[direction]), len(resulting_suborders)))
                #         logger.debug("Current multiplier is %s" % failure_multiplier)
                #         failure_multiplier *= (1 + market_MinimumBaseTrade / quantity)
                #         logger.debug("Increased multiplier is %s" % failure_multiplier)
                #         raise ValueError('OrderTooSmall')


            else:
                direction = "Buy"
                actual_coin1 = coin2
                actual_coin2 = coin1
                # if quantity < market_MinimumBaseTrade:
                #     logger.debug("ORDER TOO SMALL! 1 Market %s Orders %s" % (
                #         len(market[direction]), len(resulting_suborders)))
                #     logger.debug("Current multiplier is %s" % failure_multiplier)
                #     failure_multiplier = failure_multiplier + ((market_MinimumBaseTrade / quantity)-1)
                #     logger.debug("Increased multiplier is %s" % failure_multiplier)
                #     raise ValueError('OrderTooSmall')

                # TA ERRADO - FEE EH NO BASE MARKET
                trade_fee = Decimal(1 - (market_TradeFee / 100))

            eof = False
            while ((suborder_price < quantity and direction == "Sell") or
                   (suborder_volume < quantity and direction == "Buy")) and \
                    len(resulting_suborders) < max_orders and \
                    len(resulting_suborders) < len(market[direction]) and not eof:

                logger.debug(
                    "[. {5} .] Current suborder [{0:.20g}]: Total Price: {1:.20g} -  Total Volume: {2:.20g} - Total Requested: {3:.20g} {4}".format(
                        len(resulting_suborders) + 1,
                        suborder_price,
                        suborder_volume,
                        quantity,
                        coin1,
                        direction))

                current_volume = Decimal(market[direction][len(resulting_suborders)]["Volume"])
                current_price = Decimal(market[direction][len(resulting_suborders)]["Total"]) * Decimal(trade_fee)

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
                        logger.debug("Missing price %s " % missing_price)
                        # if missing_price < market_MinimumBaseTrade:
                        #     if len(market) == len(resulting_suborders):
                        #         raise OverflowError("Market too small!")
                        #     else:
                        #         logger.debug("ORDER TOO SMALL! 2 Market %s Orders %s" % (
                        #             len(market[direction]), len(resulting_suborders)))
                        #         logger.debug("Current multiplier is %s" % failure_multiplier)
                        #         failure_multiplier *= (1 + market_MinimumBaseTrade / missing_price)
                        #         logger.debug("Increased multiplier is %s" % failure_multiplier)
                        #         raise ValueError('OrderTooSmall')
                        order_filling_ratio = missing_price / current_price
                    else:
                        missing_volume = quantity - suborder_volume
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
                    eof = True

                resulting_suborders.append(
                    [market_id, direction, current_price * order_filling_ratio, current_volume * order_filling_ratio,
                     actual_coin1, actual_coin2, Decimal(market[direction][len(resulting_suborders)]["Price"])])
                suborder_price += current_price * order_filling_ratio
                suborder_volume += current_volume * order_filling_ratio

            return resulting_suborders


def find_common_minimum(*coins):
    return True


def three_way_probe():
    allowed_initial_markets = ["BTC", "LTC", "DOGE", "USDT", "NZDT"]

    while True:
        for coin, markets in coin_pairs.iteritems():

            logging.info("Coin %s has %s available markets: (%s)" % (coin, len(markets), ", ".join(markets)))

            for initial_market in markets:
                for intermediary_market in markets:
                    if initial_market != intermediary_market and \
                            initial_market != coin and \
                            intermediary_market != coin and \
                            initial_market in allowed_initial_markets:
                        logging.error(" .. Simulating %s>%s, %s>%s, %s>%s" % (
                            initial_market, coin, coin, intermediary_market, intermediary_market, initial_market))

                        try:

                            trade = assemble_order_quotation(minimum_order[initial_market], [initial_market, coin],
                                                             [coin, intermediary_market],
                                                             [intermediary_market, initial_market])

                            trade_initial_value = 0
                            trade_initial_market = trade[0][0]
                            trade_end_value = 0
                            trade_end_market = trade[len(trade) - 1][0]

                            for line in trade:
                                if line[0] == trade_initial_market:
                                    if line[4] == initial_market:
                                        trade_initial_value += line[2]
                                    else:
                                        trade_initial_value += line[3]
                                if line[0] == trade_end_market:
                                    if line[4] == initial_market:
                                        trade_end_value += line[2]
                                    else:
                                        trade_end_value += line[3]

                            profit = trade_end_value - trade_initial_value
                            # if True:
                            logger.info("-- Profit %s" % profit)
                            # print tabulate(trade, floatfmt=".20f")
                            if profit > 0:
                                winsound.Beep(4000, 200)
                                print "%s -> %s %s" % (trade_initial_value, trade_end_value, initial_market)
                                print tabulate(trade, floatfmt=".20f")

                                with open("profit.txt", "a") as myfile:
                                    myfile.write(
                                        "%s -> %s %s\n" % (trade_initial_value, trade_end_value, initial_market))
                                    myfile.write(tabulate(trade, floatfmt=".20f"))
                                    myfile.write("\n\n\n")

                                if len(trade) == 3:
                                    print "+++++++++++ AUTO PROCEED"

                        except OverflowError:
                            logging.info("Market is empty!")
                            continue


def two_way_probe():
    allowed_markets = ["BTC", "LTC", "USDT"]

    while True:
        for coin, markets in coin_pairs.iteritems():

            logging.info("Coin %s has %s available markets: (%s)" % (coin, len(markets), ", ".join(markets)))

            for initial_market in markets:
                for final_market in markets:
                    if initial_market != coin and \
                            final_market != coin and \
                            initial_market in allowed_markets and \
                            final_market in allowed_markets and \
                            initial_market != final_market:

                        logging.error(" .. Simulating %s>%s, %s>%s" % (
                            initial_market, coin, coin, final_market))

                        try:

                            trade = assemble_order_quotation(minimum_order[initial_market], [initial_market, coin],
                                                             [coin, final_market])


                            trade_initial_value = 0
                            trade_initial_market = trade[0][0]
                            trade_end_value = 0
                            trade_end_market = trade[len(trade) - 1][0]

                            for line in trade:
                                if line[0] == trade_initial_market:
                                    if line[4] == initial_market:
                                        trade_initial_value += line[2]
                                    else:
                                        trade_initial_value += line[3]
                                if line[0] == trade_end_market:
                                    if line[4] == final_market:
                                        trade_end_value += line[2]
                                    else:
                                        trade_end_value += line[3]

                            profit = trade_end_value * fetch_fiat(final_market) - trade_initial_value * fetch_fiat(initial_market)

                            logger.info("-- Profit %s" % profit)
                            profit_string = "%s -> %s | %s %s -> %s %s" % (trade_initial_value * fetch_fiat(initial_market),
                                                                 trade_end_value * fetch_fiat(final_market),
                                                                 trade_initial_value, initial_market,
                                                                 trade_end_value, final_market)
                            print profit_string
                            if profit > 0:
                                winsound.Beep(4000, 200)
                                print profit_string
                                print tabulate(trade, floatfmt=".20f")

                                with open("profit.txt", "a") as myfile:
                                    myfile.write(
                                        "%s -> %s %s\n" % (trade_initial_value, trade_end_value, initial_market))
                                    myfile.write(profit_string + "\n")
                                    myfile.write(tabulate(trade, floatfmt=".20f")+"\n")
                                    myfile.write("\n\n\n")


                        except OverflowError:
                            logging.info("Market is empty!")
                            continue


# Start here
# ----------------------------------------------------------------------------------------------------------------------

coin_pairs = find_market_pairs()

# three_way_probe()

two_way_probe()

# while True:
#     print fetch_fiat("BTC")
#     print fetch_fiat("LTC")
