import os
from logger_moving_strangle import logger
import logging
import datetime as dt
import sys
import pyotp
from thefirstock import thefirstock
import time 
import pandas as pd
import re
import py_vollib_vectorized
import config_moving_strangle as config

months = {
    1: 'JAN',
    2: 'FEB',
    3: 'MAR',
    4: 'APR',
    5: 'MAY',
    6: 'JUN',
    7: 'JUL',
    8: 'AUG',
    9: 'SEP',
    10: 'OCT',
    11: 'NOV',
    12: 'DEC'

}

order_index = 0
txn_type_index = 1
symbol_index = 2
quantity_index = 3
price_index = 4

quantity_dict_index = 0
buysellval_dict_index = 1
pnl_dict_index = 2

nifty_expiryday = config.nifty_expiryday  # 3 for thursday , 2 for wednesday
midcap_expiryday = config.midcap_expiryday
sensex_expiryday = config.sensex_expiryday
fin_expiryday = config.fin_expiryday
bn_expiryday = config.bn_expiryday


def send_logs(message):
    log_type = 'info'
    if log_type == 'info':
        logger.info(message)
    elif log_type == 'error':
        logger.error(message)
    elif log_type == 'debug':
        logger.debug(message)
    elif log_type == 'warning':
        logger.warning(message)
    else:
        logger.info(message)

def create_file_structure_ifnotexists(base_path):
    folder_path_with_date = base_path + '\\'
    isExist = os.path.exists(folder_path_with_date)
    if not isExist:
        os.makedirs(folder_path_with_date)
        send_logs("The new directory is created: " + base_path)

def initialize_logger(expiry_name):

    td = dt.datetime.today().date()
    # format date as yyyy-mm-dd
    td = td.strftime("%Y-%m-%d")
    if config.firstock_testing_mode:
        base_path = f"logs\\testing\\{expiry_name}_moving_strangle\\{td}\\"
    else:
        base_path = f"logs\\{expiry_name}_moving_strangle\\{td}\\"

    create_file_structure_ifnotexists(base_path)
    logging.basicConfig(filename=f"{base_path}"+f"FIRSTOCK_MOVING_STRANGLE_{td}.log", format='%(asctime)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.INFO)
    stdout_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(stdout_handler)



def login_in_firstock_Ashish():
    totp_key = 'TEST'
    # totp_key = open('my_data_firstock/totp_key.txt', 'r').read()
    # user_id = open('my_data_firstock/userId.txt', 'r').read()
    # passw = open('my_data_firstock/password.txt', 'r').read()
    # vendor_code = open('my_data_firstock/vendorCode.txt', 'r').read()
    # api_key = open('my_data_firstock/apiKey.txt', 'r').read()

    authkey = pyotp.TOTP(totp_key)
    authkey = authkey.now()
    send_logs(authkey)
    # logoutt = thefirstock.firstock_logout()
    # send_logs(logoutt)
    login = thefirstock.firstock_login(
        userId='TEST',
        password='TEST',
        TOTP=str(authkey),
        vendorCode='TEST',
        apiKey='TEST',
    )

    # login = thefirstock.firstock_login(
    #     userId = user_id,
    #     password= passw,
    #     TOTP=str(authkey),
    #     vendorCode = vendor_code,
    #     apiKey=api_key,
    # )

    send_logs("____________________FIRSTOCK LOGIN__________________________________________")
    send_logs(login)


def login_in_firstock_mummy():
    totp_key = 'TEST'

    authkey = pyotp.TOTP(totp_key)
    authkey = authkey.now()
    send_logs(authkey)
    # logoutt = thefirstock.firstock_logout()
    # send_logs(logoutt)
    login = thefirstock.firstock_login(
        userId='TEST',
        password='TEST',
        TOTP=str(authkey),
        vendorCode='TEST',
        apiKey='TEST',
    )
    logger.info("____________________FIRSTOCK LOGIN__________________________________________")
    send_logs(login)


def get_details_for_expiry(expiry_name):

    """
    Returns a dictionary containing details for a given expiry name.

    Parameters:
    expiry_name (str): Name of the expiry (nifty, banknifty, finnifty, midcap, sensex)

    Returns:
    dict: A dictionary containing the following details:
        cash_exchange_segment (str): Cash exchange segment (NSE for nifty, banknifty, finnifty, midcap; BSE for sensex)
        options_exchange_segment (str): Options exchange segment (NFO for nifty, banknifty, finnifty, midcap; BFO for sensex)
        options_instrument_type (str): Options instrument type (OPTIDX for all)
        options_symbol_name (str): Options symbol name (NIFTY for nifty, banknifty, finnifty, midcap; None for sensex)
    
    Raises:
    Exception: If an invalid expiry name is provided.
    """
    details = {}
    if expiry_name == 'nifty' or expiry_name == 'banknifty' or expiry_name == 'finnifty' or expiry_name == 'midcap':
        details['cash_exchange_segment'] = 'NSE'
        details['options_exchange_segment'] = 'NFO'
        details['options_instrument_type'] = 'OPTIDX'
        # details['options_symbol_name'] = 'NIFTY'

        if expiry_name == 'nifty':
            details['difference_between_strikes'] = 50
            details['lot_size'] = 50
        elif expiry_name == 'banknifty':
            details['difference_between_strikes'] = 100
            details['lot_size'] = 15
        elif expiry_name == 'finnifty':
            details['difference_between_strikes'] = 50
            details['lot_size'] = 40

        elif expiry_name == 'midcap':
            details['difference_between_strikes'] = 25
            details['lot_size'] = 75

    elif expiry_name == "sensex":
        details['difference_between_strikes'] = 100
        details['lot_size'] = 10

        # details['options_symbol_name'] = 'NIFTY'
    else:
        raise Exception(f"Invalid expiry name {expiry_name}")
    return details



def get_details_from_expiryname_firstock(expiry_name):
    """

    :param expiry_name: STRING: nifty, banknifty, finnifty, midcap, sensex
    :return exchange, token, token_scrip, diff_between_two_strikes
    """
    exchange = "NSE"
    token = ""
    diff_between_two_strikes = 0
    token_scrip = ""
    lot_size = 0

    details = {}

    if expiry_name == "nifty":
        exchange = "NSE"
        token = "Nifty 50"
        token_scrip = "26000"
        diff_between_two_strikes = 50
        lot_size = 50
    elif expiry_name == "banknifty":
        exchange = "NSE"
        token = "Nifty Bank"
        token_scrip = "26009"
        diff_between_two_strikes = 100
        lot_size = 15

    elif expiry_name == "finnifty":
        exchange = "NSE"
        token = "Nifty Fin Service"
        token_scrip = "26037"
        diff_between_two_strikes = 50
        lot_size = 40

    elif expiry_name == "midcap":
        exchange = "NSE"
        token = "NIFTY MID SELECT"
        token_scrip = "26074"
        diff_between_two_strikes = 25
        lot_size = 75

    elif expiry_name == "sensex":
        exchange = "BSE"
        token = "SENSEX"
        token_scrip = "1"
        diff_between_two_strikes = 100
        lot_size = 10
    else:
        raise Exception(f"Invalid expiry name {expiry_name}")

    details['exchange'] = exchange
    details['token'] = token
    details['token_scrip'] = token_scrip
    details['diff_between_two_strikes'] = diff_between_two_strikes
    details['lot_size'] = lot_size
    return details



def firstock_strike_to_symbol(expiry_name, strike, type):  # For weekly expiry
    """

        :param expiry_name: "banknifty", "nifty", "finnifty", "midcap", "sensex"
        :param strike: Integer Strike (19500 , 18500 etc)
        :param type: "CALL"/ "PUT"
        :return: Symbol for the given Strike:  Eg. NIFTY24AUG23C19000 , MIDCPNIFTY04SEP23C8000, FINNIFTY05SEP23C44000, SENSEX2390165000CE
        """
        
    global months, exp_day
    curdate = dt.datetime.today()
    curday = curdate.weekday()
    suffix = ''

    if (type == "PUT"):
        suffix = 'P'
    elif (type == "CALL"):
        suffix = 'C'

    if expiry_name == "sensex":
        exp_day = sensex_expiryday
    elif expiry_name == "midcap":
        exp_day = midcap_expiryday
    elif expiry_name == "banknifty":
        exp_day = bn_expiryday
    elif expiry_name == "nifty":
        exp_day = nifty_expiryday
    elif expiry_name == "finnifty":
        exp_day = fin_expiryday

    if curday <= exp_day:  # 0 Is Monday, 3 is Thursday
        days_remaining = exp_day - curday
    elif curday > exp_day:
        days_remaining = exp_day - curday + 7

    expirydate = curdate + dt.timedelta(days=days_remaining)  # Current upcoming expiry
    nextexpirydate = expirydate + dt.timedelta(days=7)
    nextexpirymonth = nextexpirydate.strftime("%m")

    # send_logs("Upcoming Expiry is on ", expirydate)
    expiryyear = expirydate.strftime("%y")
    expirymonth = expirydate.strftime("%m")
    expiryd = expirydate.strftime("%d")

    if (expirymonth == nextexpirymonth):
        expirytype = 'Weekly'
    else:
        expirytype = 'Monthly'

    # send_logs(expirymonth[0],expirymonth[1])

    if (expirymonth[0] == "0"):
        expirym = expirymonth[1]
    else:
        expirym = expirymonth

    # if (expirytype == 'Weekly'):
    #     symbol = "BANKNIFTY" + expiryyear + expirym + expiryd + str(strike) + suffix
    #     # symbol = "BANKNIFTY" + expiryyear + expirym + expiryd + str(strike) + suffix

    # elif (expirytype == 'Monthly'):
    prefix = ""
    if expiry_name == "sensex":
        prefix = "SENSEX"
    elif expiry_name == "midcap":
        prefix = "MIDCPNIFTY"
    elif expiry_name == "banknifty":
        prefix = "BANKNIFTY"
    elif expiry_name == "nifty":
        prefix = "NIFTY"
    elif expiry_name == "finnifty":
        prefix = "FINNIFTY"
    else:
        prefix = None

    if expiry_name == "sensex":
        # "SENSEX2390166000CE"
        # for monthly, sensex23SEP66000CE
        if type == "CALL":
            suffix = "CE"
        else:
            suffix = "PE"
        #         symbol = prefix + expiryd + months[int(expirym)] + expiryyear + suffix + str(strike)
        if expirytype == 'Monthly':
            symbol = prefix + expiryyear + months[int(expirym)] + str(strike) + suffix
        else:
            # symbol = prefix + expiryyear + str(int(expirym)) + expiryd + str(strike) + suffix
            symbol = prefix + expiryyear + months[int(expirym)][0] + expiryd + str(strike) + suffix
    else:
        symbol = prefix + expiryd + months[int(expirym)] + expiryyear + suffix + str(strike)

    return (symbol)


def last_price_firstock(symbols, symbol_index="NFO"):
    """

    :param symbols: List or String Symbol
    :param symbol_index: "NSE, NFO, BFO"
    :return: ltp array if list given , else ltp symbol
    """
    # send_logs(ltp_dict)
    if (type(symbols) is list):
        exch_symbols = []
        lastprice = []
        num_of_symbols = len(symbols)
        # send_logs(num_of_symbols)

        for i in range(num_of_symbols):
            # TODO : PLACE TRY AND CATCH THING , ERROR MANAGEMENT
            time.sleep(0.2)
            symbol_token = symbols[i]
            ltp = float(
                thefirstock.firstock_getQuoteLTP(exchange=symbol_index, token=symbol_token)['data']['lastTradedPrice'])
            lastprice.append(ltp)

        return lastprice
    else:
        try:
            ltp = float(
                thefirstock.firstock_getQuoteLTP(exchange=symbol_index, token=symbols)['data']['lastTradedPrice'])
        except Exception as e:
            time.sleep(0.3)
            ltp = float(
                thefirstock.firstock_getQuoteLTP(exchange=symbol_index, token=symbols)['data']['lastTradedPrice'])
        return ltp
        # return ltp_dict[exch_symbol]['last_price']



def weekly_future_using_firstock(expiry_name):
    """

    :param expiry_name: STRING: nifty, banknifty, finnifty, midcap, sensex
    :return: Returns synthetic future values for options/ futures
    """

    # exchange, token, token_scrip, diff_between_two_strikes = getDetailsFromExpiryName_Firstock(expiry_name)
    details = get_details_from_expiryname_firstock(expiry_name)
    exchange = details['exchange']
    token = details['token']
    token_scrip = details['token_scrip']
    diff_between_two_strikes = details['diff_between_two_strikes']


    # if is_cur_expiry_weekly() == True:

    # mod is difference in strikes (nifty has 50 strike diff between each strikes)
    try:
        symbol_cur_price = float(
            thefirstock.firstock_getQuoteLTP(exchange=exchange, token=token)['data']['lastTradedPrice'])
    except Exception as e:
        time.sleep(1)
        symbol_cur_price = float(
            thefirstock.firstock_getQuoteLTP(exchange=exchange, token=token)['data']['lastTradedPrice'])

    mod = symbol_cur_price % diff_between_two_strikes
    lower_strike = int(symbol_cur_price - mod)
    higher_strike = int(lower_strike + diff_between_two_strikes)

    if mod <= diff_between_two_strikes / 2:
        nearer_strike = lower_strike
    else:
        nearer_strike = higher_strike

    putsymbol = firstock_strike_to_symbol(expiry_name, nearer_strike, "PUT")
    callsymbol = firstock_strike_to_symbol(expiry_name, nearer_strike, "CALL")

    symbol_list = [putsymbol, callsymbol]
    symbol_index = None
    if exchange == "NSE":
        symbol_index = "NFO"
    elif exchange == "BSE":
        symbol_index = "BFO"

    try:
        ltp_list = last_price_firstock(symbol_list, symbol_index)
    except Exception as e:
        time.sleep(0.5)
        ltp_list = last_price_firstock(symbol_list, symbol_index)
    callprice = ltp_list[1]
    putprice = ltp_list[0]

    weekly_future_value = nearer_strike + callprice - putprice
    return weekly_future_value



def TIME_TO_EXPIRY_FIRSTOCK(expiry_name):
    curtime = dt.datetime.now()
    cur_minute = curtime.minute
    cur_hour = curtime.hour
    curdate = dt.datetime.today()
    curday = curdate.weekday()

    symbol_expiryday = 0
    if expiry_name == "nifty":
        symbol_expiryday = nifty_expiryday
    elif expiry_name == "banknifty":
        symbol_expiryday = bn_expiryday
    elif expiry_name == "finnifty":
        symbol_expiryday = fin_expiryday
    elif expiry_name == "midcap":
        symbol_expiryday = midcap_expiryday
    elif expiry_name == "sensex":
        symbol_expiryday = sensex_expiryday

    if curday <= symbol_expiryday:  # 0 Is Monday,1 TUE,2 WED, 3 is Thursday, 4 FRI
        days_remaining = symbol_expiryday - curday
    elif curday > symbol_expiryday:
        days_remaining = symbol_expiryday - curday + 7
    TIME_REMAINING_IN_PRESENT_DAY = 0
    if (curday == 3):  # thursday
        TIME_REMAINING_IN_PRESENT_DAY = 15.5 - cur_hour - (cur_minute / 60)  # in hours
    if (TIME_REMAINING_IN_PRESENT_DAY < 0):
        TIME_REMAINING_IN_PRESENT_DAY = 0
    else:
        TIME_REMAINING_IN_PRESENT_DAY = 15.5 - cur_hour - (cur_minute / 60)  # in hours
    TIME_REMAINING_IN_PRESENT_DAY = TIME_REMAINING_IN_PRESENT_DAY / 15.5  # in days
    ACTUAL_DAYS_TO_EXPIRY = TIME_REMAINING_IN_PRESENT_DAY + days_remaining
    t = ACTUAL_DAYS_TO_EXPIRY / 365  # TIME TO EXPIRY IN YEARS
    if (t == 0):
        t = 0.00001
    return t


def nify_get_greeks(price, curr_nifty_price, strike, t, flag):
    """
    :usage NIFTY_SPOT_CALL_IV, NIFTY_SPOT_CALL_GREEKS = nify_get_greeks(OPTION_LTP, nifty_spot_p, int(OPTION_strike), t,
                                                                     'c')
    :param price:
    :param curr_nifty_price:
    :param strike:
    :param t:
    :param flag:
    :return:
    """
    p = 0
    r = 0.05
    p = py_vollib_vectorized.vectorized_implied_volatility(price, curr_nifty_price, strike, t, r, flag, q=0,
                                                           model='black_scholes_merton',
                                                           return_as='numpy')  # equivalent
    sigma = p[0]

    # send_logs( put_ltp,"PUT IV " , putsymbol ," ", p[0]*100)

    return p[0], py_vollib_vectorized.api.get_all_greeks(flag, curr_nifty_price, strike, t, r, sigma,
                                                         model='black_scholes', return_as='dict')


def COMPLETE_SYMBOL_WATCHLIST_FIRSTOCK(expiry_name):
    """
    :param: expiry_name: "sensex", "nifty", "banknifty", "midcap", "finnifty"
    :return: 2 Dataframe  (CE AND PE )with columns : 	INDEX -> instrument_name integer_strike	instrument_token	timestamp
    last_trade_time	last_price	last_quantity	buy_quantity	sell_quantity	volume	average_price
    oi	oi_day_high	oi_day_low	net_change	lower_circuit_limit	upper_circuit_limit	IV	DELTA	THETA	GAMMA

    """
    # regex pattern set
    pattern = r'\d{4,6}'

    # nifty_prefix = nifty_current_expiry_symbol()
    details = get_details_from_expiryname_firstock(expiry_name)
    exchange = details['exchange']
    token = details['token']
    token_scrip = details['token_scrip']
    diff_between_two_strikes = details['diff_between_two_strikes']

    # nifty_strike = float(
    #     thefirstock.firstock_getQuoteLTP(exchange="NSE", token="Nifty 50")['data']['lastTradedPrice'])
    symbol_cur_price = None
    try:
        symbol_cur_price = float(
            thefirstock.firstock_getQuoteLTP(exchange=exchange, token=token)['data']['lastTradedPrice'])
    except Exception as e:
        time.sleep(1)
        symbol_cur_price = float(
            thefirstock.firstock_getQuoteLTP(exchange=exchange, token=token)['data']['lastTradedPrice'])

    nearer_strike = symbol_cur_price / diff_between_two_strikes
    mod = symbol_cur_price % diff_between_two_strikes

    if mod > diff_between_two_strikes / 2:
        nearer_strike = (int(nearer_strike) + 1) * diff_between_two_strikes
    else:
        nearer_strike = (int(nearer_strike)) * diff_between_two_strikes

    put_symbol_firstock = firstock_strike_to_symbol(expiry_name, nearer_strike, "PUT")
    call_symbol_firstock = firstock_strike_to_symbol(expiry_name, nearer_strike, "CALL")

    # put_symbol_firstock = firstock_nifty_strike_to_symbol(strike_nifty, "PUT")
    # call_symbol_firstock = firstock_nifty_strike_to_symbol(strike_nifty, "CALL")

    # for the current call_symbol_firstock (or can be put symbol, does not matter)
    # output : has status, data : {values: exchange, token, tradingsymbol, optiontype, lotsize and strikeprice}
    # we enrich this data with LTP, buy , sell , OI values in later for loop
    symbol_exchange = None
    if exchange == "NSE":
        symbol_exchange = "NFO"
    elif exchange == "BSE":
        symbol_exchange = "BFO"

    optionChain = thefirstock.firstock_OptionChain(
        exchange=symbol_exchange,
        tradingSymbol=call_symbol_firstock,
        strikePrice=str(nearer_strike),
        count="20"
    )

    # Create data token (input format to get multi-asset-quotes from firstock)
    # output: Lotsize, dayhigh,daylow, volume, lasttradedquantity, last traded price, depth (as best buy/ sell price)
    dataToken = []
    optionChainDF = None
    if (optionChain['status'] == 'Success'):
        for data in optionChain['data']:
            dataToken.append({
                "exchange": data['exchange'],
                "token": data['token']
            })

        # the getMultiQuote function gets at max 10 quotes at a time now
        enriched_data_optionchain = []
        batch_size = 20
        for i in range(0, len(dataToken), batch_size):
            time.sleep(1)
            dataToken_batch = dataToken[i:i + batch_size]
            enriched_data_optionchain_batch = thefirstock.firstock_getMultiQuote(
                dataToken=dataToken_batch
            )
            if enriched_data_optionchain_batch['status'] == 'Success':
                token_dictionary_list = enriched_data_optionchain_batch['data']
                for token_dict in token_dictionary_list:
                    enriched_data_optionchain.append(token_dict)
            else:
                time.sleep(0.2)
                enriched_data_optionchain_batch = thefirstock.firstock_getMultiQuote(
                    dataToken=dataToken_batch
                )
                if enriched_data_optionchain_batch['status'] == 'Success':
                    token_dictionary_list = enriched_data_optionchain_batch['data']
                    for token_dict in token_dictionary_list:
                        enriched_data_optionchain.append(token_dict)
                else:
                    raise Exception(
                        "Exception raised at Firststock_getMultiquote in function COMPLETE_NIFTY_WATCHLIST_FIRSTOCK()")

        # enriched_data_optionchain = thefirstock.firstock_getMultiQuote(
        #     dataToken=dataToken
        # )

        # getMultiQuotes_temp = enriched_data_optionchain
        #         send_logs(getMultiQuotes_temp)

        # Create a Dataframe from enriched_data_option_chain (Desired format -> same as Zerodha data)
        # Output: Dataframe which we get from COMPLETE_NIFTY_WATCHLIST() in Zerodha
        oc_data_list = []
        if True:
            # for data in enriched_data_optionchain['data']:
            #     pass

            columns = ["instrument_name", "instrument_token", "timestamp", "last_trade_time", "last_price",
                       "last_quantity", "buy_quantity",
                       "sell_quantity", "volume", "average_price", "oi", "oi_day_high", "oi_day_low", "net_change",
                       "lower_circuit_limit",
                       "upper_circuit_limit", "IV", "DELTA", "THETA", "GAMMA"]

            # nifty_spot_p = float(
            #     thefirstock.firstock_getQuoteLTP(exchange="NSE", token="Nifty 50")['data']['lastTradedPrice'])
            try:
                symbol_spot_p = float(
                    thefirstock.firstock_getQuoteLTP(exchange=exchange, token=token)['data']['lastTradedPrice'])
            except Exception as e:
                time.sleep(1)
                symbol_spot_p = float(
                    thefirstock.firstock_getQuoteLTP(exchange=exchange, token=token)['data']['lastTradedPrice'])

            t = TIME_TO_EXPIRY_FIRSTOCK(expiry_name=expiry_name)  # TIME TO EXPIRY IN YEARS

            # oc_data_list = []
            oc_data_list_call = []
            oc_data_list_put = []

            for data in enriched_data_optionchain:

                # in some cases , last traded price is not fetched maybe due to inliquidity.
                if 'lastTradedPrice' in data['result'].keys():
                    pass
                else:
                    continue
                dResult = data['result']
                dToken = dResult['token']
                instrument_name = dResult['tradingSymbol']
                company_name = dResult['companyName']
                instrument_token = dToken
                timestamp = dResult['requestTime']
                last_trade_time = dResult['lastTradeTime']
                last_price = dResult['lastTradedPrice']
                last_quantity = dResult['lastTradedQuantity']
                buy_quantity = None
                sell_quantity = None
                volume = dResult['volume']
                average_price = None
                oi = None
                oi_day_high = None
                oi_day_low = None
                net_change = None
                lower_circuit_limit = dResult['lowerCircuit']
                upper_circuit_limit = dResult['upperCircuit']
                IV = None
                DELTA = None
                THETA = None
                GAMMA = None

                if expiry_name == "sensex":
                    pass
                elif expiry_name == "nifty":
                    pass
                elif expiry_name == "banknifty":
                    pass
                elif expiry_name == "midcap":
                    pass
                elif expiry_name == "finnifty":
                    pass

                if expiry_name == "sensex":
                    instrument_type = data['result']['tradingSymbol'][-2:]
                else:
                    instrument_type = data['result']['tradingSymbol'][-6:-5]

                if instrument_type == 'C' or instrument_type == "CE":
                    # calculate greeks using pyvollib
                    # OPTION_strike = instrument_name[-5:]

                    # Option Strike using company name
                    # This pattern recognises 4 , 5 , 6 digit numbers in string company name of type:
                    match = re.search(pattern, company_name)
                    if match:
                        OPTION_strike = match.group()
                    OPTION_strike = int(OPTION_strike)
                    OPTION_LTP = float(last_price)
                    if (OPTION_LTP == 0):
                        OPTION_LTP = 0.05

                    NIFTY_SPOT_CALL_IV, NIFTY_SPOT_CALL_GREEKS = nify_get_greeks(OPTION_LTP, symbol_spot_p,
                                                                                 int(OPTION_strike), t, 'c')
                    NIFTY_SPOT_CALL_DELTA = NIFTY_SPOT_CALL_GREEKS['delta'][0] * 100
                    NIFTY_SPOT_PUT_IV = NIFTY_SPOT_CALL_IV * 100
                    NIFTY_SPOT_CALL_THETA = NIFTY_SPOT_CALL_GREEKS['theta'][0]
                    NIFTY_SPOT_CALL_GAMMA = NIFTY_SPOT_CALL_GREEKS['gamma'][0]

                    oc_data_list_call.append({
                        "integer_strike": OPTION_strike,
                        "instrument_name": dResult['tradingSymbol'],
                        "instrument_token": str(dToken),
                        "timestamp": dResult['requestTime'],
                        "last_trade_time": dResult['lastTradeTime'],
                        "last_price": dResult['lastTradedPrice'],
                        "last_quantity": dResult['lastTradedQuantity'],
                        "buy_quantity": None,
                        "sell_quantity": None,
                        "volume": dResult['volume'],
                        "average_price": None,
                        "oi": None,
                        "oi_day_high": None,
                        "oi_day_low": None,
                        "net_change": None,
                        "lower_circuit_limit": dResult['lowerCircuit'],
                        "upper_circuit_limit": dResult['upperCircuit'],
                        "IV": NIFTY_SPOT_CALL_IV,
                        "DELTA": NIFTY_SPOT_CALL_DELTA,
                        "THETA": NIFTY_SPOT_CALL_THETA,
                        "GAMMA": NIFTY_SPOT_CALL_GAMMA,
                    })
                elif instrument_type == 'P' or instrument_type == "PE":
                    # calculate greeks using pyvollib
                    # This pattern recognises 4 , 5 , 6 digit numbers in string company name of type:
                    match = re.search(pattern, company_name)
                    if match:
                        OPTION_strike = match.group()
                    OPTION_strike = int(OPTION_strike)

                    OPTION_LTP = float(last_price)
                    if (OPTION_LTP == 0):
                        OPTION_LTP = 0.05
                    NIFTY_SPOT_PUT_IV, NIFTY_SPOT_PUT_GREEKS = nify_get_greeks(OPTION_LTP, symbol_spot_p,
                                                                               int(OPTION_strike), t, 'p')
                    NIFTY_SPOT_PUT_DELTA = NIFTY_SPOT_PUT_GREEKS['delta'][0] * (-100)
                    NIFTY_SPOT_PUT_IV = NIFTY_SPOT_PUT_IV * 100
                    NIFTY_SPOT_PUT_THETA = NIFTY_SPOT_PUT_GREEKS['theta'][0]
                    NIFTY_SPOT_PUT_GAMMA = NIFTY_SPOT_PUT_GREEKS['gamma'][0]

                    oc_data_list_put.append({
                        "integer_strike": OPTION_strike,
                        "instrument_name": dResult['tradingSymbol'],
                        "instrument_token": str(dToken),
                        "timestamp": dResult['requestTime'],
                        "last_trade_time": dResult['lastTradeTime'],
                        "last_price": dResult['lastTradedPrice'],
                        "last_quantity": dResult['lastTradedQuantity'],
                        "buy_quantity": None,
                        "sell_quantity": None,
                        "volume": dResult['volume'],
                        "average_price": None,
                        "oi": None,
                        "oi_day_high": None,
                        "oi_day_low": None,
                        "net_change": None,
                        "lower_circuit_limit": dResult['lowerCircuit'],
                        "upper_circuit_limit": dResult['upperCircuit'],
                        "IV": NIFTY_SPOT_PUT_IV,
                        "DELTA": NIFTY_SPOT_PUT_DELTA,
                        "THETA": NIFTY_SPOT_PUT_THETA,
                        "GAMMA": NIFTY_SPOT_PUT_GAMMA,
                    })
            CALL_NIFTY_OPTION_CHAIN_df = pd.DataFrame(oc_data_list_call)
            CALL_NIFTY_OPTION_CHAIN_df.sort_values(by=['integer_strike'], inplace=True)
            #             CALL_NIFTY_OPTION_CHAIN_df.drop(['integer_strike'], axis = 1, inplace = True)
            CALL_NIFTY_OPTION_CHAIN_df.set_index('instrument_name', inplace=True)
            PUT_NIFTY_OPTION_CHAIN_df = pd.DataFrame(oc_data_list_put)
            PUT_NIFTY_OPTION_CHAIN_df.sort_values(by=['integer_strike'], inplace=True)
            #             PUT_NIFTY_OPTION_CHAIN_df.drop(['integer_strike'], axis = 1, inplace = True)
            PUT_NIFTY_OPTION_CHAIN_df.set_index('instrument_name', inplace=True)

            return CALL_NIFTY_OPTION_CHAIN_df, PUT_NIFTY_OPTION_CHAIN_df
        else:
            raise Exception(
                "Exception raised at Firststock_getMultiquote in function COMPLETE_NIFTY_WATCHLIST_FIRSTOCK()")
    else:
        raise Exception("Option Chain Function did not return desired option chain. Check immediately...")


def symbol_n_delta_strike_firstock(delta, df, put_or_call):
    """

    :param delta: INT -> Delta (1-100)
    :param df: Option Chain DF with 20 strikes, and associated data
    :param put_or_call: "p" or "c" -> put or call
    :return: strike price INT
    """
    # while (True):
    strike = 0
    if (put_or_call == "p"):

        for k, v in df.iterrows():
            if (k == '260105' or k == '256265' or k == '257801'):
                send_logs("ye ni krna")
                continue

            OPTION_strike = v["integer_strike"]
            # OPTION_strike = int(OPTION_strike[:5])
            # OPTION_LTP=v['last_price']
            OPTION_DELTA = v['DELTA']
            if (OPTION_DELTA < delta and OPTION_DELTA != 0):
                strike = int(OPTION_strike)

    elif (put_or_call == "c"):

        for k, v in df.iterrows():
            if (k == '260105' or k == '256265' or k == '257801'):
                send_logs("ye ni krna")
                continue

            OPTION_strike = v["integer_strike"]
            # OPTION_strike = int(OPTION_strike[:5])
            # OPTION_LTP=v['last_price']
            OPTION_DELTA = v['DELTA']
            if (OPTION_DELTA < delta and OPTION_DELTA != 0):
                strike = int(OPTION_strike)
                return strike

    return strike


# Expiry Fucntions
def is_cur_expiry_weekly(expiry_name="nifty"):  # Returns True for a weekly expiry and False for a monthly expiry
    global months
    curdate = dt.datetime.today()
    curday = curdate.weekday()
    symbol_expiryday = 0

    if expiry_name == "nifty":
        symbol_expiryday = nifty_expiryday
    elif expiry_name == "banknifty":
        symbol_expiryday = bn_expiryday
    elif expiry_name == "sensex":
        symbol_expiryday = sensex_expiryday
    elif expiry_name == 'midcap':
        symbol_expiryday = midcap_expiryday
    elif expiry_name == 'finnifty':
        symbol_expiryday = fin_expiryday
    else:
        raise Exception("Invalid Expiry Name")

    if curday <= symbol_expiryday:  # 0 Is Monday, 3 is Thursday
        days_remaining = symbol_expiryday - curday
    elif curday > symbol_expiryday:
        days_remaining = symbol_expiryday - curday + 7

    expirydate = curdate + dt.timedelta(days=days_remaining)  # Current upcoming expiry
    nextexpirydate = expirydate + dt.timedelta(days=7)

    nextexpirymonth = nextexpirydate.strftime("%m")
    expirymonth = expirydate.strftime("%m")

    if (expirymonth == nextexpirymonth):
        return True
    else:
        return False


def fetch_order_firstock(order_id):
    """
    :param order_id: order id to fetch order with: INT
    :return: Order Details for given (PLACED) order with order_id  \ String  -=> order has "Status" and Data Array with history of order(pending, mordify, success etc)
    """
    # order id is string
    error_msg = "Couldn\'t find that `order_id`"
    singleOrderHistory = None
    count = 0
    while True:
        try:
            count += 1
            singleOrderHistory = thefirstock.firstock_SingleOrderHistory(
                orderNumber=order_id
            )
        except Exception as e:
            if count > 5:
                send_logs("Fetch Order Max attempts crossed ...Exiting")
                return None
            elif error_msg in str(e):
                send_logs("Order id not found")
                send_logs("Count-", count, "Exception Caught Running again!")
                time.sleep(1)

        if (len(singleOrderHistory) != 0):
            break

    return singleOrderHistory


def execute_order_firstock_v2(symbol, type_, quant, price, trig_price, product, expiry_name="nifty"):
    """

    :param symbol: Symbol to sell EX: 'NIFTY24AUG23C19600' , 'SENSEX2391566600PE'
    :param type_: BUY or SELL
    :param quant: quantity to sell / buy
    :param price: price to buy or sell (can be none)
    :param trig_price: For SL orders: price to buy or sell (can be none)
    :param product: NRML or MIS for zerodha
    :param expiry_name: STRING "sensex", "nifty", "banknifty", "finnifty", "midcap"
    :return: Order Id for the successful orders
    """
    #     global kite

    sl_limit_error = "Trigger price for stoploss buy orders cannot be above the upper circuit price. Please try placing the order with trigger price below"
    limit_lower_circuit_error = "Your order price is lower than the current [lower circuit limit]"
    error3 = "Trigger price for stoploss buy orders should be higher than the last traded price "
    error4 = "Price for stoploss buy orders cannot be above the upper circuit price. Please try placing the order with Price below"

    if type_ == "BUY":
        txn_type = 'B'
    elif type_ == "SELL":
        txn_type = 'S'

    product_type = 'I'  # C / M / I C -> Cash and Carry, M -> F&O Normal, I -> Intraday

    if expiry_name == "sensex":
        exchange = "BFO"
    else:
        exchange = "NFO"
    orderid = None
    if price == None and trig_price == None:  # It means Market order but I need to place my range checks in place an convert it into SL order
        order_type = "LMT"
        strike_lastprice = 0
        try:

            symbol_current_details = thefirstock.firstock_getQuote(exchange=exchange, token=symbol)
            strike_lastprice = float(symbol_current_details['data']['lastTradedPrice'])  # throws error if not fetched
        except Exception as e:
            time.sleep(0.3)
            try:
                symbol_current_details = thefirstock.firstock_getQuoteLTP(exchange=exchange, token=symbol)
                strike_lastprice = float(
                    symbol_current_details['data']['lastTradedPrice'])  # throws error if not fetched
            except Exception as e:
                send_logs(e)
                send_logs("Exception raised at execute_order() function, order was not executed. Check immediately...")
                return None

        # send_logs(symbol_current_details)
        # send_logs()
        upper_circuit_limit = float(symbol_current_details['data']['upperCircuit'])
        lower_circuit_limit = float(symbol_current_details['data']['lowerCircuit'])
        if (strike_lastprice > upper_circuit_limit) or (strike_lastprice < lower_circuit_limit):
            send_logs("Tried to place order above upper circuit limit or lower circuit limit!!!")
            send_logs("Returning without taking any trade. Potential FAT FINGER TRADE Detected!!!")
            return None

        trig_price = 0
        price = 0

        if strike_lastprice < 800:  # Improve this range check
            if type_ == "BUY":  # Giving 15 % room to execute on all orders
                price = round(1.15 * strike_lastprice, 1)
                # price = strike_lastprice
            elif type_ == "SELL":
                price = round(0.85 * strike_lastprice, 1)
                # price = strike_lastprice

            # Here Trig Price will remain None
            # send_logs("Placing Order ", str(type), " ", symbol, "for Quantity ", str(quant), "at Rs. ", strike_lastprice)
            logging.info("Placing Order %s  %s for Quantity %s at Rs. %s", str(type_), symbol, str(quant),
                         strike_lastprice)
        else:
            logging.info("Price out of range detected. Not placing the order!!!")
            return None

        if config.firstock_testing_mode:
            price = strike_lastprice

    elif (price != None and trig_price != None):
        order_type = "SL-LMT"  # Order type stop loss  and SL orders.
        # send_logs("Placing SL Order ", str(type), " ", symbol, "for Quantity ", str(quant), "at Rs. ", trig_price)
        logging.info("Placing SL Order %s  %s for Quantity %s at Rs. %s", str(type_), symbol, str(quant), trig_price)
    elif (price != None and trig_price == None):
        order_type = "LMT"  # Order type Limit.
        # send_logs("Placing Limit Order ", str(type), " ", symbol, "for Quantity ", str(quant), "at Rs. ", price)
        logging.info("Placing Limit Order %s  %s for Quantity %s at Rs. %s", str(type_), symbol, str(quant), price)

    # logging.info("trig price is %s price is %s", trig_price, price)
    send_logs("Taking Trade for Symbol: " + str(symbol) + " Trade Type: " + type_)

    try:
        order_execution_result = thefirstock.firstock_placeOrder(
            exchange=exchange,
            tradingSymbol=symbol,
            quantity=quant,
            price=price,
            product=product_type,
            transactionType=txn_type,
            priceType=order_type,
            retention="DAY",
            triggerPrice=trig_price,
            remarks="Python Package Order"
        )

        if (order_execution_result["status"] == "Failed"):
            raise Exception(
                "Exception raised at execute_order() function, order was not executed. Check immediately...")
        send_logs("Order Id is - " + str(order_execution_result['data']["orderNumber"]))
        orderid = str(order_execution_result['data']["orderNumber"])
        # Place orders for hedges as well
    except Exception as e:
        send_logs(e)
        send_logs("Exception raised at execute_order() function, order was not executed. Check immediately...")
    finally:
        pass
        # send_logs("Exception Caught")

    return orderid




def symbol_to_strike_firstock(symbol, expiry_name="nifty"):
    """
    :param symbol: String: EX NIFTY24AUG23P19300, SENSEX2391566000CE
    :param expiry_name: String: "nifty","banknifty", "sensex", "midcap", "finnifty"
    :return: String strike 19300 or 0
    """
    if symbol == None or type(symbol) != str:
        send_logs(
            "Incorrect Symbol !!!" + "You are trying to reference Symbol: " + str(symbol) + " which is wrong!")
        return 0

    if expiry_name == "sensex":
        instrument_type = symbol[-2:]
    else:
        instrument_type = symbol[-6:-5]

    # instrument_type = symbol[-6:-5]
    # For midcap , make someother function! since it is near 10000 (5 digit number ) but still is 4 digit number
    OPTION_strike = 0
    if ((instrument_type == 'C') or (instrument_type == 'P')) and (
            expiry_name == "nifty" or expiry_name == "banknifty" or expiry_name == "finnifty"):
        # calculate greeks using pyvollib
        OPTION_strike = symbol[-5:]
        OPTION_strike = int(OPTION_strike)
        return OPTION_strike
    elif instrument_type == "CE" or instrument_type == "PE":
        OPTION_strike = symbol[-7:-2]
        OPTION_strike = int(OPTION_strike)
        return OPTION_strike
    else:
        send_logs(
            "Incorrect Symbol !!!" + "You are trying to reference Symbol: " + str(symbol) + " which is wrong!")
        return OPTION_strike




def write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f):
    curtime = dt.datetime.now()
    if config.firstock_testing_mode:
        executed_price = order['price']
    else:
        executed_price = order['averagePrice']
    f.write(f"{orderid}\t{buy_or_sell}\t{symbol}\t{quantity}\t{executed_price}\t{curtime}\n")


def put_strike_up_moving_strangle_firstock_v2(diff, putstrike, quantity, product_type, filename, expiry_name="nifty"):
    """

    :param diff: INT - HOW MUCH TO MOVE UP
    :param putstrike: INT/STRING - CURRENT PUT STRIKE
    :param quantity: INT
    :param product_type: NOT USED
    :param filename: ORDERS FILENAME
    :param expiry_name: "nifty" or "banknifty" or "finnifty" or "sensex" or "midcap"
    """

    f = open(filename, "a")  # Append mode
    newstrike = int(putstrike) + diff
    cursymbol = firstock_strike_to_symbol(expiry_name, putstrike, 'PUT')
    newsymbol = firstock_strike_to_symbol(expiry_name, newstrike, 'PUT')
    # send_logs("Inside call up, product type is :", type)

    curtime = dt.datetime.now()
    orderid = execute_order_firstock_v2(symbol=cursymbol, type_="BUY", quant=quantity, price=None, trig_price=None,
                                        product=product_type, expiry_name=expiry_name)
    time.sleep(0.5)
    order = fetch_order_firstock(orderid)['data'][0]

    if order['status'] == success_status_firstock:
        buy_or_sell = "BUY"
        symbol = cursymbol
        write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
    else:
        time.sleep(2)
        if order['status'] == success_status_firstock:

            buy_or_sell = "BUY"
            symbol = cursymbol
            write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
        else:
            send_logs("Something Wrong with Order CHeck Now")

    curtime = dt.datetime.now()
    orderid = execute_order_firstock_v2(symbol=newsymbol, type_="SELL", quant=quantity, price=None, trig_price=None,
                                        product=product_type, expiry_name=expiry_name)
    time.sleep(0.3)
    order = fetch_order_firstock(orderid)['data'][0]
    if order['status'] == success_status_firstock:

        buy_or_sell = "SELL"
        symbol = newsymbol
        write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
    else:
        time.sleep(2)
        if order['status'] == success_status_firstock:

            buy_or_sell = "SELL"
            symbol = newsymbol
            write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
        else:
            send_logs("Something Wrong with Order CHeck Now")

    f.close()


def call_strike_down_moving_strangle_firstock_v2(diff, callstrike, quantity, product_type, filename,
                                                 expiry_name="nifty"):
    """

        :param diff: INT - HOW MUCH TO MOVE UP
        :param putstrike: INT/STRING - CURRENT PUT STRIKE
        :param quantity: INT
        :param product_type: NOT USED
        :param filename: ORDERS FILENAME
        :param expiry_name: "nifty" or "banknifty" or "finnifty" or "sensex" or "midcap"
    """

    f = open(filename, "a")  # Append mode

    newstrike = int(callstrike) - diff

    cursymbol = firstock_strike_to_symbol(expiry_name, callstrike, 'CALL')
    newsymbol = firstock_strike_to_symbol(expiry_name, newstrike, 'CALL')

    curtime = dt.datetime.now()
    orderid = execute_order_firstock_v2(symbol=cursymbol, type_="BUY", quant=quantity, price=None, trig_price=None,
                                        product=product_type, expiry_name=expiry_name)

    time.sleep(0.5)
    order = fetch_order_firstock(orderid)['data'][0]

    if (order['status'] == success_status_firstock):

        buy_or_sell = "BUY"
        symbol = cursymbol
        write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)

    else:

        time.sleep(2)

        if (order['status'] == success_status_firstock):

            buy_or_sell = "BUY"
            symbol = cursymbol
            write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
        else:
            send_logs("Something Wrong with Order CHeck Now")

    curtime = dt.datetime.now()
    orderid = execute_order_firstock_v2(symbol=newsymbol, type_="SELL", quant=quantity, price=None, trig_price=None,
                                        product=product_type, expiry_name=expiry_name)
    time.sleep(0.3)
    order = fetch_order_firstock(orderid)['data'][0]
    if (order['status'] == success_status_firstock):

        buy_or_sell = "SELL"
        symbol = newsymbol
        write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
    else:
        time.sleep(2)
        if (order['status'] == success_status_firstock):

            buy_or_sell = "SELL"
            symbol = newsymbol
            write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
        else:
            send_logs("Something Wrong with Order CHeck Now")

    f.close()


def call_strike_up_moving_strangle_firstock_v2(diff, callstrike, quantity, product_type, filename, expiry_name="nifty"):
    """

        :param diff: INT - HOW MUCH TO MOVE UP
        :param putstrike: INT/STRING - CURRENT PUT STRIKE
        :param quantity: INT
        :param product_type: NOT USED
        :param filename: ORDERS FILENAME
        :param expiry_name: "nifty" or "banknifty" or "finnifty" or "sensex" or "midcap"
        """

    f = open(filename, "a")  # Append mode

    newstrike = int(callstrike) + diff

    cursymbol = firstock_strike_to_symbol(expiry_name, callstrike, 'CALL')
    newsymbol = firstock_strike_to_symbol(expiry_name, newstrike, 'CALL')

    curtime = dt.datetime.now()
    orderid = execute_order_firstock_v2(symbol=cursymbol, type_="BUY", quant=quantity, price=None, trig_price=None,
                                        product=product_type, expiry_name=expiry_name)

    time.sleep(0.5)
    order = fetch_order_firstock(orderid)['data'][0]
    send_logs("Here \n Order fetched BUY Order")
    if (order['status'] == success_status_firstock):

        buy_or_sell = "BUY"
        symbol = cursymbol
        write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
    else:

        time.sleep(2)

        if (order['status'] == success_status_firstock):

            buy_or_sell = "BUY"
            symbol = cursymbol
            write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
        else:
            send_logs("Something Wrong with Order CHeck Now")

    curtime = dt.datetime.now()
    orderid = execute_order_firstock_v2(symbol=newsymbol, type_="SELL", quant=quantity, price=None, trig_price=None,
                                        product=product_type, expiry_name=expiry_name)
    time.sleep(0.3)
    order = fetch_order_firstock(orderid)['data'][0]
    if (order['status'] == success_status_firstock):

        buy_or_sell = "SELL"
        symbol = newsymbol

        # def write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f):

        write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
    else:
        time.sleep(2)
        if (order['status'] == success_status_firstock):

            buy_or_sell = "SELL"
            symbol = newsymbol
            write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
        else:
            send_logs("Something Wrong with Order CHeck Now")

    f.close()


def put_strike_down_moving_strangle_firstock_v2(diff, putstrike, quantity, product_type, filename, expiry_name="nifty"):
    """

        :param diff: INT - HOW MUCH TO MOVE UP
        :param putstrike: INT/STRING - CURRENT PUT STRIKE
        :param quantity: INT
        :param product_type: NOT USED
        :param filename: ORDERS FILENAME
        :param expiry_name: "nifty" or "banknifty" or "finnifty" or "sensex" or "midcap"
    """

    curdate = dt.datetime.today()
    # filename = curdate.strftime("%d") + curdate.strftime("%m") + curdate.strftime("%y") + "MovingStrangle.txt"
    f = open(filename, "a")  # Append mode

    newstrike = int(putstrike) - diff

    cursymbol = firstock_strike_to_symbol(expiry_name, putstrike, 'PUT')
    newsymbol = firstock_strike_to_symbol(expiry_name, newstrike, 'PUT')

    curtime = dt.datetime.now()
    orderid = execute_order_firstock_v2(symbol=cursymbol, type_="BUY", quant=quantity, price=None, trig_price=None,
                                        product=product_type, expiry_name=expiry_name)

    time.sleep(0.5)
    order = fetch_order_firstock(orderid)['data'][0]

    if (order['status'] == success_status_firstock):

        buy_or_sell = "BUY"
        symbol = cursymbol
        write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
    else:

        time.sleep(2)

        if (order['status'] == success_status_firstock):

            buy_or_sell = "BUY"
            symbol = cursymbol
            write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
        else:
            send_logs("Something Wrong with Order CHeck Now")

    curtime = dt.datetime.now()
    orderid = execute_order_firstock_v2(symbol=newsymbol, type_="SELL", quant=quantity, price=None, trig_price=None,
                                        product=product_type, expiry_name=expiry_name)
    time.sleep(0.3)
    order = fetch_order_firstock(orderid)['data'][0]
    if (order['status'] == success_status_firstock):

        buy_or_sell = "SELL"
        symbol = newsymbol
        write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
    else:
        time.sleep(2)
        if (order['status'] == success_status_firstock):

            buy_or_sell = "SELL"
            symbol = newsymbol
            write_order_to_file(order, orderid, symbol, buy_or_sell, quantity, f)
        else:
            send_logs("Something Wrong with Order CHeck Now")

    f.close()




def monitor_symbol_moving_strangle_with_delta_multiple_firstock(product_type, call_diff, put_diff,
                                                                filename, expiry_name="nifty"):  # Based on Orderid
    """

    :param product_type: 'NRML' , 'MIS' from Zerodha
    :param call_diff: INT , Ex: 300, 200 etc
    :param put_diff: INT , Ex: 300, 200 etc
    :param filename: Orders file to save orders to.
    :param expiry_name: STRING - "nifty", "banknifty", "sensex", "finnifty", "midcap"
    :param firstock_testing_mode: BOOLEAN - TRUE, FALSE
    :return: current pnl of running position
    """

    global order_index, txn_type_index, symbol_index, quantity_index, price_index, success_status_firstock

    success_status_firstock = config.success_status_firstock

    callsymbol = ""
    putsymbol = ""

    curtime = dt.datetime.now()
    cur_hour = curtime.hour
    curdate = dt.datetime.today()
    curday = curdate.weekday()

    # filename = curdate.strftime("%d") + curdate.strftime("%m") + curdate.strftime("%y") + "MovingStrangle.txt"
    f = open(filename, "r")  # Append mode
    filedata = f.read()
    f.close()

    order_data = filedata.splitlines()
    num_orders = len(order_data)
    processed_order_data = []

    for i in range(num_orders):  # Processes Data fetched from file and stores it as a 2D array in processed_order_data
        processed_order_data.append(order_data[i].split('\t'))
    # send_logs("Data fetched from file is- \n" )
    # psend_logs(processed_order_data)
    symbol_dict = {}

    for i in range(num_orders):  # Here a dictionary of all symbols found in orders is created
        symbol = processed_order_data[i][symbol_index]
        if (symbol in symbol_dict.keys()):
            pass  # Do Nothing equivalent in python
        else:  # Add symbol to dictionary
            symbol_dict[symbol] = [0, 0, 0]  # quantity, BuySellValue,pnl

    for i in range(num_orders):  # PNL Calculation
        BuySellValue = 0  # persymbol
        type = processed_order_data[i][txn_type_index]
        symbol = processed_order_data[i][symbol_index]  # fetch symbol
        quantity = int(processed_order_data[i][quantity_index])
        symbol_avg_price = processed_order_data[i][price_index]
        # send_logs("sold price of symbol : " + symbol + " is: "+str(symbol_avg_price))
        # send_logs("LTP for symbol : " + symbol + " is: "+str(last_price_firstock(symbol)))

        if (type == 'SELL'):
            quantity = (int(quantity) * -1)
        elif (type == 'BUY'):
            quantity = int(quantity)
        # send_logs(symbol_list)

        BuySellValue += (int(quantity) * float(symbol_avg_price))

        symbol_dict[symbol][1] += BuySellValue
        symbol_dict[symbol][0] += quantity
    pnl = 0.0
    # psend_logs(symbol_dict)
    # send_logs("Step 3")

    symbol_exchange = "NFO"
    if expiry_name == "sensex":
        symbol_exchange = "BFO"
    else:
        symbol_exchange = "NFO"

    for symbol in symbol_dict:  # Calculates Total PNL and Finds our current SELL Legs
        quantity = symbol_dict[symbol][0]
        try:
            symbol_dict[symbol][2] = (symbol_dict[symbol][1] * -1) + (
                    quantity * last_price_firstock(symbol, symbol_exchange))  # symbolpnl = BuySellValue+ (Quantity*LTP)
        except Exception as e:
            time.sleep(0.5)
            symbol_dict[symbol][2] = (symbol_dict[symbol][1] * -1) + (
                    quantity * last_price_firstock(symbol, symbol_exchange))  # symbolpnl = BuySellValue+ (Quantity*LTP)

        pnl += symbol_dict[symbol][2]

        # Instrument_type : C or CE , P or PE
        if expiry_name == "sensex":
            instrument_type = symbol[-2:]
        else:
            instrument_type = symbol[-6:-5]

        # if quantity < 0 and (symbol[-6:-5] == 'P'):
        #     putsymbol = symbol
        #     putquantity = int(quantity)
        # elif quantity < 0 and (symbol[-6:-5] == 'C'):
        #     callsymbol = symbol
        #     callquantity = int(quantity)
        #     send_logs("Call symbol is " + callsymbol + " and quantity is " + str(callquantity))

        if quantity < 0 and (instrument_type == 'P' or instrument_type == 'PE'):
            putsymbol = symbol
            putquantity = int(quantity)
            send_logs("Put symbol is " + putsymbol + " and quantity is " + str(putquantity))
        elif quantity < 0 and (instrument_type == 'C' or instrument_type == 'CE'):
            callsymbol = symbol
            callquantity = int(quantity)
            send_logs("Call symbol is " + callsymbol + " and quantity is " + str(callquantity))


    if expiry_name == "sensex":
        diff_plus = 200
        diff_minus = 100
    elif expiry_name == "nifty":
        diff_plus = 46
        diff_minus = 46
    elif expiry_name == "banknifty":
        diff_plus = 200
        diff_minus = 100
    elif expiry_name == "midcap":
        diff_plus = 50
        diff_minus = 25
    elif expiry_name == "finnifty":
        diff_plus = 46
        diff_minus = 46
    else:
        send_logs("Wrong input expiry_name recieved, returning none!")
        return None
    
    call_max_range = call_diff + config.call_diff_plus
    call_min_range = call_diff - config.call_diff_minus
    put_max_range = put_diff + diff_plus
    put_min_range = put_diff - diff_minus


    symbol_cur_price = weekly_future_using_firstock(expiry_name)
    send_logs(f"CURRENTLY {expiry_name} IS AT: " + str(symbol_cur_price))

    ########## Define Move Up strike for each symbol ##########
    strike_adjustment = config.strike_adjustment
    # if expiry_name == "nifty":
    #     strike_adjustment = 50  # pts
    # elif expiry_name == "banknifty":
    #     strike_adjustment = 200  # pts
    # elif expiry_name == "finnifty":
    #     strike_adjustment = 50  # pts
    # elif expiry_name == "sensex":
    #     strike_adjustment = 200  # pts
    # elif expiry_name == "midcap":
    #     strike_adjustment = 50  # pts

    if (callsymbol == "" and putsymbol == ""):
        send_logs("PLEASE TAKE SOME POSITIONS")
        return 0.0
    else:
        # callstrike = nifty_symbol_to_strike_firstock(callsymbol)
        # putstrike = nifty_symbol_to_strike_firstock(putsymbol)

        callstrike = symbol_to_strike_firstock(callsymbol, expiry_name)
        putstrike = symbol_to_strike_firstock(putsymbol, expiry_name)

        put_diff = symbol_cur_price - putstrike
        call_diff = callstrike - symbol_cur_price

        if put_diff < put_max_range and put_diff > put_min_range:
            send_logs("Put Diff is in range, no action needed!!!" + " Put_Min_Range: " + str(
                put_min_range) + " < PutDiff: " + str(put_diff) + " < Put_max_range: " + str(put_max_range))

        if put_diff > put_max_range:
            # time.sleep(5)
            send_logs("Put Strike Diff is " + str(put_diff) + " Moving Puts Up")
            put_strike_up_moving_strangle_firstock_v2(strike_adjustment, putstrike, abs(putquantity), "product_type",
                                                      filename, expiry_name)
        elif put_diff < put_min_range:
            # time.sleep(5)
            send_logs("Put Strike Diff is " + str(put_diff) + " Moving Puts Down")
            put_strike_down_moving_strangle_firstock_v2(strike_adjustment, putstrike, abs(putquantity), "product_type",
                                                        filename, expiry_name)
        else:
            send_logs("Put Strike Diff is " + str(put_diff) + " Nothing to do right now !!")
            send_logs("Will Move Puts Up At " + str(putstrike + put_max_range))
            send_logs("Will Move Puts Down At " + str(putstrike + put_min_range))

        if call_diff > call_max_range:
            # time.sleep(5)
            send_logs("Call Strike Diff is " + str(call_diff) + " Moving Calls Down")
            call_strike_down_moving_strangle_firstock_v2(strike_adjustment, callstrike, abs(callquantity),
                                                         "product_type", filename, expiry_name)
        elif call_diff < call_min_range:
            # time.sleep(5)
            send_logs("Call Strike Diff is " + str(call_diff) + " Moving Calls Up")
            call_strike_up_moving_strangle_firstock_v2(strike_adjustment, callstrike, abs(callquantity), "product_type",
                                                       filename, expiry_name)
        else:
            send_logs("Call Strike Diff is " + str(call_diff) + " Nothing to do right now !!")
            send_logs("Will Move Calls Up At " + str(callstrike - call_min_range))
            send_logs("Will Move Calls Down At " + str(callstrike - call_max_range))

    return round(pnl, 1)


def exit_nifty_moving_strangle_multiple_firstock_v2(product_type, filename, expiry_name="nifty"):  # Based on Orderid
    """
    Quits all open positions (BUY OR SELL) from order file only
    :param product_type: "NRML" or "MIS"
    :param filename: Order File
    """
    global order_index, txn_type_index, symbol_index, quantity_index, price_index

    callsymbol = ""
    putsymbol = ""

    curtime = dt.datetime.now()
    curdate = dt.datetime.today()

    # filename = curdate.strftime("%d") + curdate.strftime("%m") + curdate.strftime("%y") + "MovingStrangle.txt"
    f = open(filename, "r")  # Read mode
    filedata = f.read()
    f.close()

    order_data = filedata.splitlines()
    num_orders = len(order_data)
    processed_order_data = []

    for i in range(num_orders):  # Processes Data fetched from file and stores it as a 2D array in processed_order_data
        processed_order_data.append(order_data[i].split('\t'))
    # send_logs("Data fetched from file is- \n" )
    # psend_logs(processed_order_data)
    symbol_dict = {}

    for i in range(num_orders):  # Here a dictionary of all symbols found in orders is created
        symbol = processed_order_data[i][symbol_index]
        if (symbol in symbol_dict.keys()):
            pass  # Do Nothing equivalent in python
        else:  # Add symbol to dictionary
            symbol_dict[symbol] = [0, 0, 0]  # quantity, BuySellValue,pnl

    for i in range(num_orders):  # Net Quantity Calculation
        BuySellValue = 0  # persymbol
        type = processed_order_data[i][txn_type_index]
        symbol = processed_order_data[i][symbol_index]  # fetch symbol
        quantity = processed_order_data[i][quantity_index]

        if (type == 'SELL'):
            quantity = (int(quantity) * -1)
        elif (type == 'BUY'):
            quantity = int(quantity)
        # send_logs(symbol_list)

        symbol_dict[symbol][0] += quantity

    f = open(filename, "a")  # Append Mode
    for symbol in symbol_dict:  # Exit Sell Positions
        quantity = symbol_dict[symbol][0]
        if quantity < 0:
            send_logs("Exiting "+ symbol)
            curtime = dt.datetime.now()
            orderid = execute_order_firstock_v2(symbol=symbol, type_="BUY", quant=abs(quantity), price=None,
                                                trig_price=None,
                                                product=product_type, expiry_name=expiry_name)
            f.write(str(orderid) + "\t" + "BUY" + "\t" + symbol + "\t" + str(abs(quantity)) + "\t" + str(
                fetch_order_firstock(orderid)['data'][0]['price']) + "\t" + str(curtime) + "\n")

    for symbol in symbol_dict:  # Exit Buy Positions
        quantity = symbol_dict[symbol][0]
        if quantity > 0:
            send_logs("Exiting "+ symbol)
            curtime = dt.datetime.now()
            orderid = execute_order_firstock_v2(symbol=symbol, type_="SELL", quant=abs(quantity), price=None,
                                                trig_price=None,
                                                product=product_type, expiry_name=expiry_name)
            f.write(str(orderid) + "\t" + "SELL" + "\t" + symbol + "\t" + str(abs(quantity)) + "\t" + str(
                fetch_order_firstock(orderid)['data'][0]['price']) + "\t" + str(curtime) + "\n")

    f.close()