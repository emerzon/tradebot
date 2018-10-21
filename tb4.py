# Stupid imports
import simplejson as json
import requests

from tabulate import tabulate
import winsound
import pprint

from decimal import *
import logging
import datetime
import time


from cryptopia_api import Api
api_wrapper = Api("","")

# Init settings
getcontext().prec = 9
fiat_ttl = 60

# Variable inits
failure_multiplier = Decimal(1).normalize()
s = requests.Session()
fiat_values = {}
fiat_lastcheck = {}
trade_pairs={}

minimum_order = {"BTC": Decimal(0.0005 * 1.002).normalize(),
                 "LTC": Decimal(0.052 * 1.002).normalize(),
                 "DOGE": Decimal(300 * 1.002).normalize(),
                 "USDT": Decimal(1 * 1.002).normalize(),
                 "NZDT": Decimal(1 * 1.002).normalize()}

max_orders = 5

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
    if coin in ["BTC", "LTC", "DOGE"]:
        last_check = fiat_lastcheck.get(coin, datetime.datetime(1970, 1, 1))
        if (datetime.datetime.now() - last_check).total_seconds() > fiat_ttl:
            if coin in ["BTC", "LTC"]:
                value = Decimal(requests.get("https://api.coinbase.com/v2/prices/%s-USD/sell" % coin).json()['data']['amount']).normalize()
            else:
                value = Decimal(requests.get("https://api.cryptowat.ch/markets/kraken/dogebtc/summary").json()['result']['price']['last']) * fetch_fiat("BTC").normalize()
            fiat_values[coin] = value
            fiat_lastcheck[coin] = datetime.datetime.now()
        return fiat_values[coin]
    elif coin in ["USDT"]:
        return Decimal(0.999).normalize()
    else:
        return 0

def find_market_pairs():
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
    global trade_pairs
    for item in trade_pairs:
        if item["Label"] == "%s/%s" % (coin1, coin2) or item["Label"] == "%s/%s" % (coin2, coin1):
            if coin1 == item["BaseSymbol"]:
                reversed_market = True
            else:
                reversed_market = False
            return item["Id"], reversed_market


def find_market_coins(market_id):
    global trade_pairs
    for item in trade_pairs:
        print item["Id"]
        if item["Id"] == market_id:
            return [item["Symbol"], item["BaseSymbol"]]
    return None


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

    failure_multiplier = Decimal(1).normalize()

    for i in range(0, 300):
        if i == 100:
            raise OverflowError("Deu merda")
        quantity = initial_quantity
        try:
            resulting_orders = []
            for coin1, coin2 in pairs:
                if len(resulting_orders) == 0:
                    actual_quantity = Decimal(quantity).normalize() * Decimal(failure_multiplier).normalize()
                else:
                    actual_quantity = Decimal(quantity).normalize()
                suborder = assemble_suborder(coin1, coin2, actual_quantity, orders)

                if suborder is None or len(suborder) == 0:
                    raise OverflowError('Empty market!')

                suborder_price = Decimal(sum(Decimal(row[2]) for row in suborder)).normalize()
                suborder_volume = Decimal(sum(Decimal(row[3]) for row in suborder)).normalize()

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

    if orders["Data"] is None:
        raise ValueError("No orders in this market")

    for market in orders["Data"]:
        if market["TradePairId"] == market_id:

            resulting_suborders = []
            suborder_price = Decimal(0).normalize()
            suborder_volume = Decimal(0).normalize()

            for item in trade_pairs:
                if market_id == item["Id"]:
                    market_TradeFee = Decimal(item["TradeFee"]).normalize()
                    market_MinimumBaseTrade = Decimal(item["MinimumBaseTrade"]) * 1 + (market_TradeFee / 100).normalize()
                    market_BaseSymbol = item["BaseSymbol"]

            logger.debug(
                "[....] TradePairId is {0} [MiniminumBaseTrade {1:.20g}]".format(market_id, market_MinimumBaseTrade))

            if reversed_market:
                direction = "Sell"
                actual_coin1 = coin1
                actual_coin2 = coin2
                trade_fee = Decimal(1 + (market_TradeFee / 100)).normalize()

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
                trade_fee = Decimal(1 - (market_TradeFee / 100)).normalize()

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

                current_volume = Decimal(market[direction][len(resulting_suborders)]["Volume"]).normalize()
                current_price = Decimal(market[direction][len(resulting_suborders)]["Total"]) * Decimal(trade_fee).normalize()

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
                        missing_price = Decimal(quantity) - Decimal(suborder_price).normalize()
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
                    [market_id, direction, Decimal(current_price * order_filling_ratio).normalize(), Decimal(current_volume * order_filling_ratio).normalize(),
                     actual_coin1, actual_coin2, Decimal(market[direction][len(resulting_suborders)]["Price"]).normalize()])
                suborder_price += Decimal(current_price * order_filling_ratio).normalize()
                suborder_volume += Decimal(current_volume * order_filling_ratio).normalize()

            return resulting_suborders


def find_common_minimum(*coins):
    return True

def do_trade(orders):
    logging.debug("--!!!!! Executing %s trade orders!" % len(orders))
    print orders
    for market, trade_type, coin1_total, rate, coin1, coin2, coin2_total in orders:
        #BUY
        if trade_type == "Buy":
            real_trade = "Sell"
            watch_coin = coin2
            watch_value = rate
            real_rate = coin2_total
            real_amount = coin1_total
        #SELL
        else:
            real_trade = "Buy"
            watch_coin = coin1
            real_rate = coin2_total
            real_amount = rate
            watch_value = coin1_total
        logger.debug("------ Market: %s - %s, %s, %s, %s, %s, %s" % (
        market, trade_type, coin1_total, real_amount, coin1, coin2, coin2_total))
        counter = 0
        coin_balance = 0

        while (watch_value > coin_balance) and counter < 20:
            balance = api_wrapper.get_balance(watch_coin)
            print balance
            if balance[0] is not None:
                coin_balance = Decimal(balance[0]["Available"]).normalize()
            logging.debug("Current %s balance: %s" % (watch_coin, coin_balance))
            logging.debug("Current %s order: %s" % (watch_coin, watch_value))
            logging.debug("Awaiting for balance... %s" % counter)
            counter += 1
        if counter == 20:
            raise ValueError("Balance wait fail!")

        p1 = market
        p2 = real_trade
        p3 = str(real_rate.normalize())
        p4 = str(real_amount.normalize())

        logger.debug("Here the jurupoca piates - %s %s %s %s" % (p1, p2, p3, p4))
        submission = api_wrapper.submit_trade(market=p1, trade_type=p2, rate=p3, amount=p4)

        logger.debug(submission)
        with open("orders.log", "a") as f:
            f.write("[%s] - %s %s %s %s\n" % (str(time.strftime("%b %d %Y %H:%M:%S", time.gmtime())), p1, p2, p3, p4))
            f.write(str(submission))
            f.write("\n")
        #if submission[0] is None:
        #    raise ValueError("Error submiting order!")
    logger.info("Trade executed!!!!")
    return True

def three_way_probe():
    allowed_initial_markets = ["BTC", "LTC"]

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
    allowed_markets = ["BTC", "DOGE", "LTC"]
    allowed_initial_markets = ["BTC"]


    while True:
        for coin, markets in coin_pairs.iteritems():

            logging.info("Coin %s has %s available markets: (%s)" % (coin, len(markets), ", ".join(markets)))

            for initial_market in markets:
                for final_market in markets:
                    if initial_market != coin and \
                            final_market != coin and \
                            initial_market in allowed_markets and \
                            final_market in allowed_markets and \
                            initial_market != final_market and \
                            initial_market in allowed_initial_markets:

                        logging.error(" .. Simulating %s>%s, %s>%s" % (
                            initial_market, coin, coin, final_market))

                        try:

                            trade = assemble_order_quotation(minimum_order[initial_market], [initial_market, coin],
                                                             [coin, final_market])


                            trade_initial_value = 0
                            trade_initial_market = trade[0][0]
                            trade_end_value = 0
                            trade_end_market = trade[len(trade) - 1][0]

                            cols = zip(*trade)


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
                            if profit > 0 and len(trade) == 2:
                                winsound.Beep(3000, 200)
                                print profit_string
                                print tabulate(trade, floatfmt=".20f")

                                with open("profit.txt", "a") as myfile:
                                    myfile.write(
                                        "%s -> %s %s\n" % (trade_initial_value, trade_end_value, initial_market))
                                    myfile.write(profit_string + "\n")
                                    myfile.write(tabulate(trade, floatfmt=".20f")+"\n")
                                    myfile.write("\n\n\n")


                                    #try:
                                    do_trade(trade)
                                    #except ValueError:

                                    #    logging.info("No balance for trade!")



                        except OverflowError:
                            logging.info("Market is empty!")
                            continue


# Start here
# ----------------------------------------------------------------------------------------------------------------------

coin_pairs = find_market_pairs()

two_way_probe()





