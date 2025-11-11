# initialise logger and set logger file path according to expiry name and today's date
# use logger_moving_strangle.py to initialise logger
from datetime import datetime
import datetime as dt
from logger_moving_strangle import logger
import logging
import os
import sys
import config_moving_strangle as config
import time
import py_vollib.black_scholes
import py_vollib.black_scholes_merton.implied_volatility
import py_vollib_vectorized
import pandas as pd
import shutil
import xlwings as xw
import numpy as np
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
bankex_expiryday = config.bankex_expiryday
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
    # create a folder with date of today

    isExist = os.path.exists(folder_path_with_date)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(folder_path_with_date)
        # send_logs("The new directory is created: " + base_path)


def initialize_logger(expiry_name):

    td = datetime.today().date()
    # format date as yyyy-mm-dd
    td = td.strftime("%Y-%m-%d")
    if config.testing_mode:
        base_path = f"logs\\testing\\{expiry_name}_moving_strangle\\{td}\\"
    else:
        base_path = f"logs\\{expiry_name}_moving_strangle\\{td}\\"
    create_file_structure_ifnotexists(base_path)
    logging.basicConfig(filename=f"{base_path}"+f"KOTAK_MOVING_STRANGLE_{td}.log", format='%(asctime)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.INFO)
    stdout_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(stdout_handler)


def excel_initialisation(datafiles_base_path, expiry_name):
    if config.enable_excel:
        base_path_excel = datafiles_base_path
        create_file_structure_ifnotexists(base_path_excel)

        source_excel_path = "C:\\Users\\ashis\\OneDrive\\Desktop\\run_sheet_code_folder\\kotak_Neo_Codes\\datafiles\\"
        source_excel_file_with_path = source_excel_path + f"Algo_sheet.xlsx"
        destination_excel_file_with_path = base_path_excel + f"{expiry_name}_running_algo_sheet.xlsx"
        excel_file_name = f"{expiry_name}_running_algo_sheet.xlsx"

        if os.path.isfile(destination_excel_file_with_path):
            print('Excel file already exists, Code will continue to use it...')
        else:
            print('Creating Excel File : '+destination_excel_file_with_path)
            shutil.copy(source_excel_file_with_path, destination_excel_file_with_path)

        # define excel sheet for streaming pnl data to...
        wb = xw.Book(destination_excel_file_with_path)
        sheet = wb.sheets['Sheet1']

        return sheet
    else:
        return None


def set_excel_values(curtime, pnl_points, delta, symbol, buy_sell, quantity, price):
    if config.enable_excel:
        config.sheet.range('A' + str(config.sheet_index)).value = str(curtime)
        config.sheet.range('B' + str(config.sheet_index)).value = config.excel_pnl_points
        config.sheet.range('C' + str(config.sheet_index)).value = delta
        config.sheet.range('D' + str(config.sheet_index)).value = symbol
        config.sheet.range('E' + str(config.sheet_index)).value = buy_sell
        config.sheet.range('F' + str(config.sheet_index)).value = quantity
        config.sheet.range('G' + str(config.sheet_index)).value = price

        config.sheet_index += 1
    else:
        pass

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
        details['cash_exchange_segment'] = 'BSE'
        details['options_exchange_segment'] = 'BFO'
        details['options_instrument_type'] = 'OPTIDX'
        details['difference_between_strikes'] = 100
        details['lot_size'] = 10
    elif expiry_name == "bankex":
        details['cash_exchange_segment'] = 'BSE'
        details['options_exchange_segment'] = 'BFO'
        details['options_instrument_type'] = 'OPTIDX'
        details['difference_between_strikes'] = 100
        details['lot_size'] = 15

        # details['options_symbol_name'] = 'NIFTY'
    else:
        raise Exception(f"Invalid expiry name {expiry_name}")
    return details

def get_current_time():
    curtime = dt.datetime.now()
    cur_minute = curtime.minute
    cur_hour = curtime.hour
    curdate = dt.datetime.today()
    return curtime, cur_minute,cur_hour,curdate

def get_exchange_segment(expiry_name):
    instrument_token = None
    exchange_segment = None
    if expiry_name == 'sensex':
        instrument_token = '1'
        exchange_segment = 'bse_cm'
    elif expiry_name == "bankex":
        instrument_token = '12'
        exchange_segment = 'bse_cm'
    elif expiry_name == "nifty":
        instrument_token = '26000'
        exchange_segment = 'nse_cm'
    elif expiry_name == "banknifty":
        instrument_token = '26009'
        exchange_segment = 'nse_cm'
    elif expiry_name == "midcap":
        instrument_token = '26074'
        exchange_segment = 'nse_cm'
    elif expiry_name == "finnifty":
        instrument_token = '26037'
        exchange_segment = 'nse_cm'
    else:
        raise Exception('Invalid expiry name')
    return instrument_token, exchange_segment

def get_ltp_for_index_using_kotak(expiry_name):
    instrument_token = None
    exchange_segment = None
    if expiry_name == 'sensex':
        instrument_token = '1'
        exchange_segment = 'bse_cm'
    elif expiry_name == "bankex":
        instrument_token = '12'
        exchange_segment = 'bse_cm'
    elif expiry_name == "nifty":
        instrument_token = '26000'
        exchange_segment = 'nse_cm'
    elif expiry_name == "banknifty":
        instrument_token = '26009'
        exchange_segment = 'nse_cm'
    elif expiry_name == "midcap":
        instrument_token = '26074'
        exchange_segment = 'nse_cm'
    elif expiry_name == "finnifty":
        instrument_token = '26037'
        exchange_segment = 'nse_cm'
    else:
        raise Exception('Invalid expiry name')
    max_retry_count = 3
    for i in range(max_retry_count):
        try:
            time.sleep(0.3)
            instrument_tokens = [{"instrument_token": instrument_token, "exchange_segment": exchange_segment}]
            quote = config.NEO_OBJ.quotes(instrument_tokens = instrument_tokens, quote_type="", isIndex=False)
            ltp =  quote['message'][0]['last_traded_price']
            return ltp
        except:
            pass

    return None

def strike_to_symbol_kotak(expiry_name, strike, type):  # For weekly expiry
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
    elif expiry_name == "bankex":
        exp_day = bankex_expiryday
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
        # send_logs("Current upcoming expiry is a Weekly Expiry")
        expirytype = 'Weekly'
    else:
        # send_logs("Current upcoming expiry is a Monthly Expiry")
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
    elif expiry_name == "bankex":
        prefix = "BANKEX"
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

    if type == "CALL":
        suffix = "CE"
    else:
        suffix = "PE"
    #         symbol = prefix + expiryd + months[int(expirym)] + expiryyear + suffix + str(strike)
        
    ##############################  NEW CODE (DELETE on next run) #########################################
    if expiry_name == "banknifty":
        expirytype = 'Weekly'
    ####################################################################################
    
    if expirytype == 'Monthly':
        symbol = prefix + expiryyear + months[int(expirym)] + str(strike) + suffix
    else:
        # if expiry_name == "bankex":
        #     symbol = prefix + expiryyear + str(expirym) + expiryd + str(strike) + suffix
        # else:
        # # symbol = prefix + expiryyear + str(int(expirym)) + expiryd + str(strike) + suffix
        #     symbol = prefix + expiryyear + months[int(expirym)][0] + expiryd + str(strike) + suffix
        symbol = prefix + expiryyear + str(expirym) + expiryd + str(strike) + suffix

    return (symbol)

def symbol_to_strike_kotak(symbol, expiry_name):
    if 'MIDCPNIFTY' in symbol:
        strike = int(symbol[-7:-2])
    else:
        strike = int(symbol[-7:-2])
    return strike




    
        

def get_option_data_kotak(symbol, expiry_name):
    client = config.NEO_OBJ
    # symbol_data = config.TOKEN_MAP[config.TOKEN_MAP['pTrdSymbol'] == symbol]
    symbol_data = config.TOKEN_MAP.loc[config.TOKEN_MAP['pTrdSymbol'] == symbol]

    if len(symbol_data) == 0:
        send_logs(f'Invalid symbol {symbol}')
        return None

    symbol_token = symbol_data.iloc[0]['pSymbol']

    if expiry_name == "sensex" or expiry_name == "bankex":
        exchange_segment = "bse_fo"
    else:
        exchange_segment = "nse_fo"
    instrument_tokens = [{"instrument_token": str(symbol_token), "exchange_segment": exchange_segment}]
    message = client.quotes(instrument_tokens = instrument_tokens, quote_type="", isIndex=False)
    if message['message'] == []:
        send_logs(f"Returning [] for symbol {symbol}")
        return []
    return message['message'][0]

# execute_order_kotak(nifty_symbol, "SELL", 1, None, None, "NRML","DAY", "nifty")
def execute_order_kotak(symbol, type_, quant, price, trig_price, product, validity, expiry_name):

    client = config.NEO_OBJ
    if expiry_name == 'sensex' or expiry_name == "bankex":
        exchange_segment = "bse_fo"
    else:
        exchange_segment = "nse_fo"
    if type_ == "BUY":
        transaction_type = 'B'
    elif type_ == "SELL":
        transaction_type = 'S'

    if price == None and trig_price == None:
        order_type = "L"
        strike_lastprice = 0
        try:
            symbol_current_details = get_option_data_kotak(symbol, expiry_name)
            strike_lastprice = float(symbol_current_details['last_traded_price'])
            print(strike_lastprice)
        except Exception as e:
            try:
                time.sleep(0.3)
                symbol_current_details = get_option_data_kotak(symbol, expiry_name)
                strike_lastprice = float(symbol_current_details['last_traded_price'])
            except Exception as e:
                send_logs(e)
                send_logs("Error in getting LTP")
                return None

        upper_circuit_limit = float(symbol_current_details['upper_circuit_limit'])
        lower_circuit_limit = float(symbol_current_details['lower_circuit_limit'])
        
        if config.testing_mode: 
            send_logs(f"Upper Circuit Limit is {upper_circuit_limit} and Lower Circuit Limit is {lower_circuit_limit} and Symbol is {symbol}")

        if (strike_lastprice > upper_circuit_limit) or (strike_lastprice < lower_circuit_limit):
            send_logs("Tried to place order above upper circuit limit or lower circuit limit!!!")
            send_logs("Returning without taking any trade. Potential FAT FINGER TRADE Detected!!!")
            return None
        trig_price = 0
        price = 0

        if float(strike_lastprice) < 800:  # Improve this range check
            if type_ == "BUY":  # Giving 15 % room to execute on all orders
                price = round(1.15 * float(strike_lastprice), 1)
            elif type_ == "SELL":
                price = round(0.85 * float(strike_lastprice), 1)

            send_logs(f"Placing Order {type_} {symbol} for Quantity {quant} at Rs. {strike_lastprice}")
        else:
            send_logs("Price out of range detected. Not placing the order!!!")

    elif (price != None and trig_price != None):
        order_type = "SL"  # Order type stop loss  and SL orders.
        send_logs(f"Placing SL Order {type_} {symbol} for Quantity {quant} at Rs. {trig_price}")
    elif (price != None and trig_price == None):
        order_type = "L"  # Order type Limit.
        send_logs(f"Placing Limit Order {type_} {symbol} for Quantity {quant} at Rs. {price}")

    # logging.info("trig price is %s price is %s", trig_price, price)
    send_logs("Taking Trade for Symbol: " + str(symbol) + " Trade Type: " + type_)
    # return None

    if config.testing_mode:
        price = strike_lastprice
    try:
    # Place a Order
        order_execution_result = client.place_order(
            exchange_segment=exchange_segment,
            product=product,
            price=str(price),
            order_type=order_type,
            quantity=str(quant),
            validity=validity,
            trading_symbol=symbol,
            transaction_type=transaction_type,
            amo="NO",
            trigger_price=str(trig_price),
            tag=None
        )
        send_logs(order_execution_result)
        if order_execution_result['stCode'] != 200:
            raise Exception(
                "Exception raised at execute_order() function, order was not executed. Check immediately...")
        order_id = order_execution_result['nOrdNo']
        time.sleep(0.3)
    except Exception as e:
        send_logs(e)
        send_logs("Exception raised at execute_order() function, order was not executed. Check immediately...")
        return None
    return order_id



def last_price_kotak(symbols, expiry_name, symbol_index="NFO"):

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
            try:
                ltp = float(get_option_data_kotak(str(symbol_token), expiry_name)['last_traded_price'])
            except Exception as e:
                time.sleep(0.3)
                ltp = float(get_option_data_kotak(str(symbol_token), expiry_name)['last_traded_price'])
            lastprice.append(ltp)
        return lastprice
    else:
        symbol_token = symbols
        try:
            ltp = float(get_option_data_kotak(str(symbol_token), expiry_name)['last_traded_price'])

        except Exception as e:
            time.sleep(0.3)
            ltp = float(get_option_data_kotak(str(symbol_token), expiry_name)['last_traded_price'])
        return ltp


def get_ltp_for_symbol_from_datafeed_using_websocket(symbol):
    if symbol in config.datafeed:
        try:
            ltp =  float(config.datafeed[symbol]['ltp'])
            return ltp
        except Exception as e:
            time.sleep(1) # 1 second later, ltp might be present
            ltp =  float(config.datafeed[symbol]['ltp'])
            return ltp
    else:
        time.sleep(1)
        try:
            if symbol in config.datafeed:
                ltp =  float(config.datafeed[symbol]['ltp'])
                return ltp
        except Exception as e:
            raise Exception(f"Symbol {symbol} not found in datafeed")


def last_price_kotak_using_websocket(symbols):
    if (type(symbols) is list):
        lastprice = []
        num_of_symbols = len(symbols)
        for i in range(num_of_symbols):
            time.sleep(0.1)
            symbol_name = symbols[i]
            ltp = get_ltp_for_symbol_from_datafeed_using_websocket(symbol_name)
            lastprice.append(ltp)
        return lastprice
    else:
        symbol_name = symbols
        return get_ltp_for_symbol_from_datafeed_using_websocket(symbol_name)

def weekly_future_using_kotak_using_websocket():
    expiry_name = config.expiry_name
    details = get_details_for_expiry(expiry_name)
    diff_between_two_strikes = details['difference_between_strikes']
    # diff_between_two_strikes = 50
    # needs expiry_name for this compulsarily
    symbol_cur_price = float(get_ltp_for_symbol_from_datafeed_using_websocket(expiry_name))
    mod = symbol_cur_price % diff_between_two_strikes
    lower_strike = int(symbol_cur_price - mod)
    higher_strike = int(lower_strike + diff_between_two_strikes)
    if mod <= diff_between_two_strikes / 2:
        nearer_strike = lower_strike
    else:
        nearer_strike = higher_strike

    putsymbol = strike_to_symbol_kotak(expiry_name, nearer_strike, "PUT")
    callsymbol = strike_to_symbol_kotak(expiry_name, nearer_strike, "CALL")
    callprice = last_price_kotak_using_websocket(callsymbol)
    putprice = last_price_kotak_using_websocket(putsymbol)
    weekly_future_value = nearer_strike + callprice - putprice
    return weekly_future_value


def get_option_data_kotak_using_websocket(symbol):
    try:
        if symbol in config.datafeed:
            return config.datafeed[symbol]
    except Exception as e:
        time.sleep(1)
        try:
            if symbol in config.datafeed:
                return config.datafeed[symbol]
        except Exception as e:
            raise Exception(f"Symbol {symbol} not found in datafeed")

# TODO Test this function
def execute_order_kotak_using_websocket(symbol, type_, quant, price, trig_price, product, validity):
    expiry_name = config.expiry_name
    client = config.NEO_OBJ
    if expiry_name == 'sensex' or expiry_name == "bankex":
        exchange_segment = "bse_fo"
    else:
        exchange_segment = "nse_fo"
    if type_ == "BUY":
        transaction_type = 'B'
    elif type_ == "SELL":
        transaction_type = 'S'

    if price == None and trig_price == None:
        order_type = "L"
        strike_lastprice = 0
        try:
            symbol_current_details = get_option_data_kotak_using_websocket(symbol)
            strike_lastprice = float(get_ltp_for_symbol_from_datafeed_using_websocket(symbol))
            print(f"Strike Last Price is {strike_lastprice} for symbol {symbol} and expiry {expiry_name}")
        except Exception as e:
            try:
                time.sleep(1)
                strike_lastprice = float(last_price_kotak_using_websocket(symbol))
                print(f"Strike Last Price is {strike_lastprice} for symbol {symbol} and expiry {expiry_name}")
            except Exception as e:
                send_logs(e)
                send_logs("Error in getting LTP")
                return None
        # try:
        #     upper_circuit_limit = float(symbol_current_details['ucl'])
        #     lower_circuit_limit = float(symbol_current_details['lcl'])
        # except Exception as e:
        #     time.sleep(1)
        #     try:
        #         upper_circuit_limit = float(symbol_current_details['ucl'])
        #         lower_circuit_limit = float(symbol_current_details['lcl']) 
        #     except Exception as e:
        #         raise Exception("Upper Circuit Limit and Lower Circuit Limit not found")
            
        # if config.testing_mode: 
        #     send_logs(f"Upper Circuit Limit is {upper_circuit_limit} and Lower Circuit Limit is {lower_circuit_limit} and Symbol is {symbol}")

        # if (strike_lastprice > upper_circuit_limit) or (strike_lastprice < lower_circuit_limit):
        #     send_logs("Tried to place order above upper circuit limit or lower circuit limit!!!")
        #     send_logs("Returning without taking any trade. Potential FAT FINGER TRADE Detected!!!")
        #     return None
        trig_price = 0
        price = 0

        if float(strike_lastprice) < 800:  # Improve this range check
            if type_ == "BUY":  # Giving 15 % room to execute on all orders
                price = round(1.15 * float(strike_lastprice), 1)
            elif type_ == "SELL":
                price = round(0.85 * float(strike_lastprice), 1)

            send_logs(f"Placing Order {type_} {symbol} for Quantity {quant} at Rs. {strike_lastprice}")
        else:
            send_logs("Price out of range detected. Not placing the order!!!")

    elif (price != None and trig_price != None):
        order_type = "SL"  # Order type stop loss  and SL orders.
        send_logs(f"Placing SL Order {type_} {symbol} for Quantity {quant} at Rs. {trig_price}")
    elif (price != None and trig_price == None):
        order_type = "L"  # Order type Limit.
        send_logs(f"Placing Limit Order {type_} {symbol} for Quantity {quant} at Rs. {price}")

    # logging.info("trig price is %s price is %s", trig_price, price)
    send_logs("Taking Trade for Symbol: " + str(symbol) + " Trade Type: " + type_)
    # return None

    if config.testing_mode:
        price = strike_lastprice
    try:
    # Place a Order
        order_execution_result = client.place_order(
            exchange_segment=exchange_segment,
            product=product,
            price=str(price),
            order_type=order_type,
            quantity=str(quant),
            validity=validity,
            trading_symbol=symbol,
            transaction_type=transaction_type,
            amo="NO",
            trigger_price=str(trig_price),
            tag=None
        )
        send_logs(order_execution_result)
        if order_execution_result['stCode'] != 200:
            raise Exception(
                "Exception raised at execute_order() function, order was not executed. Check immediately...")
        order_id = order_execution_result['nOrdNo']
        time.sleep(0.3)
    except Exception as e:
        send_logs(e)
        send_logs("Exception raised at execute_order() function, order was not executed. Check immediately...")
        return None
    return order_id

# TODO - check if this is working
def close_position_kotak_using_websocket(symbol, quantity, filename):
    
    product_type = config.producttype
    validity = config.validity  
    expiry_name = config.expiry_name
    
    curtime = dt.datetime.now()
    f = open(filename, "a")  # Append mode

    orderid = execute_order_kotak_using_websocket(symbol=symbol, type_="BUY", quant=quantity, price=None, trig_price=None,
                                        product=product_type, validity = validity, expiry_name=expiry_name)
    time.sleep(0.5)
    fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
    if fetched_order[0]['ordSt'] == config.success_status_kotak:
        if config.testing_mode:
            executed_price = fetched_order[0]['prc']
        else:
            executed_price = fetched_order[0]['avgPrc']
        f.write(f"{orderid}\tBUY\t{symbol}\t{quantity}\t{executed_price}\n")
        # set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = symbol, buy_sell= "BUY", quantity=quantity, price = executed_price)
    else:
        time.sleep(1)
        fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
        if fetched_order[0]['ordSt'] == config.success_status_kotak:
            if config.testing_mode:
                executed_price = fetched_order[0]['prc']
            else:
                executed_price = fetched_order[0]['avgPrc']
            f.write(f"{orderid}\tBUY\t{symbol}\t{quantity}\t{executed_price}\n")
            # set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = symbol, buy_sell= "BUY", quantity=quantity, price = executed_price)

        else:
            send_logs("Something Wrong with Order CHeck Now")
            # todo , exit the put position and exit the program

    f.close()
    
def weekly_future_using_kotak(expiry_name):
    """
    Calculates the weekly synthetic future value using Kotak securities API.

    Parameters:
    expiry_name (str): The name of the expiry date for the option contract.

    Returns:
    float: The calculated weekly synthetic future value.
    """
    details = get_details_for_expiry(expiry_name)
    diff_between_two_strikes = details['difference_between_strikes']
    # diff_between_two_strikes = 50
    symbol_cur_price = float(get_ltp_for_index_using_kotak(expiry_name))
    mod = symbol_cur_price % diff_between_two_strikes
    lower_strike = int(symbol_cur_price - mod)
    higher_strike = int(lower_strike + diff_between_two_strikes)
    if mod <= diff_between_two_strikes / 2:
        nearer_strike = lower_strike
    else:
        nearer_strike = higher_strike

    putsymbol = strike_to_symbol_kotak(expiry_name, nearer_strike, "PUT")
    callsymbol = strike_to_symbol_kotak(expiry_name, nearer_strike, "CALL")
    symbol_list = [putsymbol, callsymbol]
    ltp_list = last_price_kotak(symbol_list, expiry_name)
    callprice = float(ltp_list[1])
    putprice = float(ltp_list[0])
    weekly_future_value = nearer_strike + callprice - putprice
    return weekly_future_value

def TIME_TO_EXPIRY(expiry_name):
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
    elif expiry_name == "bankex":
        symbol_expiryday = bankex_expiryday
    else:
        raise Exception("Invalid expiry name")

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

def symbol_get_greeks(price, curr_nifty_price, strike, t, flag):
    """
    Calculates the implied volatility and greeks for a given option symbol.
    
    Usage:
        NIFTY_SPOT_CALL_IV, NIFTY_SPOT_CALL_GREEKS = symbol_get_greeks(OPTION_LTP, nifty_spot_p, int(OPTION_strike), t,
                                                                     'c')
    Args:
        price (float): The price of the option.
        curr_nifty_price (float): The current price of the underlying asset.
        strike (float): The strike price of the option.
        t (float): The time to expiration of the option (in years).
        flag (str): The type of option ('call' or 'put').

    Returns:
        tuple: A tuple containing the implied volatility (float) and a dictionary of greeks (dict).
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


def COMPLETE_OPTION_CHAIN_KOTAK_USING_WEBSOCKET(depth = 30):
    call_df = []    
    put_df = []
    symbol_ltp_map = {}
    symbol_volume_map = {}  
    for key, value in config.datafeed.items():
        if 'ltp' in value:
            symbol_ltp_map[key] = value['ltp']
        if 'v' in value: 
            # TODO - possible that volume data does not come? 
            symbol_volume_map[key] = value['v']    
            
    for key, value in config.call_symbol_to_strike_map.items():
        if key in symbol_ltp_map:
            call_df.append([float(symbol_ltp_map[key]), key, value])
        else:
            print(key, value, "Not found")
    # print()
    for key, value in config.put_symbol_to_strike_map.items():
        if key in symbol_ltp_map:
            # print(key, value, symbol_ltp_map[key])
            put_df.append([float(symbol_ltp_map[key]), key, value ])
        else:
            print(key, value, "Not found")
    symbol_cur_price = float(config.datafeed[config.expiry_name]['ltp'])
    quotes_put_df = pd.DataFrame(put_df, columns = ['last_traded_price', 'symbol', 'strike' ])
    quotes_call_df = pd.DataFrame(call_df, columns = ['last_traded_price', 'symbol', 'strike' ])    
    
    t = TIME_TO_EXPIRY(config.expiry_name)
    quotes_call_df['IV'] = quotes_call_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'c')[0] * 100, axis=1)
    quotes_call_df['DELTA'] = quotes_call_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'c')[1]['delta'][0] * 100, axis=1)
    quotes_call_df['THETA'] = quotes_call_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'c')[1]['theta'][0], axis=1)
    quotes_call_df['GAMMA'] = quotes_call_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'c')[1]['gamma'][0], axis=1)
    quotes_call_df['VEGA'] = quotes_call_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'c')[1]['vega'][0], axis=1)
    
    
    quotes_put_df['IV'] = quotes_put_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'p')[0] * 100, axis=1)
    quotes_put_df['DELTA'] = quotes_put_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'p')[1]['delta'][0] * (-100), axis=1)
    quotes_put_df['THETA'] = quotes_put_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'p')[1]['theta'][0], axis=1)
    quotes_put_df['GAMMA'] = quotes_put_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'p')[1]['gamma'][0], axis=1)
    quotes_put_df['VEGA'] = quotes_put_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'p')[1]['vega'][0], axis=1)
    config.call_option_chain_current = quotes_call_df
    config.put_option_chain_current = quotes_put_df
    return quotes_call_df, quotes_put_df
    
def COMPLETE_SYMBOL_WATCHLIST_KOTAK(expiry_name , depth = 30):

    client = config.NEO_OBJ
    details = get_details_for_expiry(expiry_name)
    diff_between_two_strikes = details['difference_between_strikes']
    # diff_between_two_strikes = 50

    symbol_cur_price = float(get_ltp_for_index_using_kotak(expiry_name))

    nearer_strike = symbol_cur_price / diff_between_two_strikes
    mod = symbol_cur_price % diff_between_two_strikes
    if mod > diff_between_two_strikes / 2:
        nearer_strike = (int(nearer_strike) + 1) * diff_between_two_strikes
    else:
        nearer_strike = (int(nearer_strike)) * diff_between_two_strikes

    atm_call_symbol_kotak  = strike_to_symbol_kotak(expiry_name, nearer_strike, "CALL")
    atm_put_symbol_kotak = strike_to_symbol_kotak(expiry_name, nearer_strike, "PUT")

    # based on depth and difference between two strikes, get strikes for watchlist
    strikes = [strike for strike in range(nearer_strike - depth * diff_between_two_strikes, nearer_strike + depth * diff_between_two_strikes, diff_between_two_strikes)]
    call_instrument_tokens = []
    put_instrument_tokens = []

    for strike in strikes:
        call_symbol_kotak  = strike_to_symbol_kotak(expiry_name, strike, "CALL")
        put_symbol_kotak = strike_to_symbol_kotak(expiry_name, strike, "PUT")

        symbol_data = config.TOKEN_MAP.loc[config.TOKEN_MAP['pTrdSymbol'] == call_symbol_kotak]
        if len(symbol_data) == 0:
            send_logs(f'Invalid symbol {call_symbol_kotak}')
            continue

        symbol_token = symbol_data.iloc[0]['pSymbol']
        if expiry_name == 'sensex' or expiry_name == "bankex":
            exchange_segment = "bse_fo"
        else:
            exchange_segment = "nse_fo"

        call_instrument_tokens.append({"instrument_token": str(symbol_token), "exchange_segment": exchange_segment})

        symbol_data = config.TOKEN_MAP.loc[config.TOKEN_MAP['pTrdSymbol'] == put_symbol_kotak]
        if len(symbol_data) == 0:
            send_logs(f'Invalid symbol {put_symbol_kotak}')
            continue
        symbol_token = symbol_data.iloc[0]['pSymbol']
        if expiry_name == 'sensex' or expiry_name == "bankex":
            exchange_segment = "bse_fo"
        else:
            exchange_segment = "nse_fo"
        put_instrument_tokens.append({"instrument_token": str(symbol_token), "exchange_segment": exchange_segment})
    try:
        quotes_call =  client.quotes(instrument_tokens = call_instrument_tokens, quote_type="", isIndex=False)
        quotes_put = client.quotes(instrument_tokens = put_instrument_tokens, quote_type="", isIndex=False)
    except Exception as e:
        time.sleep(0.3)
        quotes_call =  client.quotes(instrument_tokens = call_instrument_tokens, quote_type="", isIndex=False)
        quotes_put = client.quotes(instrument_tokens = put_instrument_tokens, quote_type="", isIndex=False)

    quotes_call_df = pd.DataFrame(quotes_call['message'])
    quotes_put_df = pd.DataFrame(quotes_put['message'])

    if expiry_name == "midcap":
        if symbol_cur_price>10000:
            quotes_call_df['strike'] = quotes_call_df['trading_symbol'].apply(lambda x: int(x[-7:-2]))
            quotes_put_df['strike'] = quotes_put_df['trading_symbol'].apply(lambda x: int(x[-7:-2]))
        else:
            quotes_call_df['strike'] = quotes_call_df['trading_symbol'].apply(lambda x: int(x[-6:-2]))
            quotes_put_df['strike'] = quotes_put_df['trading_symbol'].apply(lambda x: int(x[-6:-2]))
    else:
        quotes_call_df['strike'] = quotes_call_df['trading_symbol'].apply(lambda x: int(x[-7:-2]))
        quotes_put_df['strike'] = quotes_put_df['trading_symbol'].apply(lambda x: int(x[-7:-2]))

    quotes_call_df = quotes_call_df.sort_values(by=['strike'])
    quotes_call_df = quotes_call_df.reset_index(drop=True)
    quotes_put_df = quotes_put_df.sort_values(by=['strike'])
    quotes_put_df = quotes_put_df.reset_index(drop=True)
    quotes_call_df['strike'] = quotes_call_df['strike'].astype(int)
    quotes_put_df['strike'] = quotes_put_df['strike'].astype(int)
    quotes_call_df['last_traded_price'] = quotes_call_df['last_traded_price'].astype(float)
    quotes_put_df['last_traded_price'] = quotes_put_df['last_traded_price'].astype(float)


    t = TIME_TO_EXPIRY(expiry_name)
    
    # apply msf.msf.symbol_get_greeks(OPTION_LTP, symbol_cur_price, int(OPTION_strike), t,'c') over each row of quotes_call_df and store in new column each of IV, DELTA, THETA, GAMMA
    quotes_call_df['IV'] = quotes_call_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'c')[0] * 100, axis=1)
    quotes_call_df['DELTA'] = quotes_call_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'c')[1]['delta'][0] * 100, axis=1)
    quotes_call_df['THETA'] = quotes_call_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'c')[1]['theta'][0], axis=1)
    quotes_call_df['GAMMA'] = quotes_call_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'c')[1]['gamma'][0], axis=1)

    quotes_put_df['IV'] = quotes_put_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'p')[0] * 100, axis=1)
    quotes_put_df['DELTA'] = quotes_put_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'p')[1]['delta'][0] * (-100), axis=1)
    quotes_put_df['THETA'] = quotes_put_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'p')[1]['theta'][0], axis=1)
    quotes_put_df['GAMMA'] = quotes_put_df.apply(lambda row: symbol_get_greeks(row['last_traded_price'], symbol_cur_price, row['strike'], t,'p')[1]['gamma'][0], axis=1)

    return quotes_call_df, quotes_put_df

# TODO - CHECK THIS FUNCTION
def symbol_n_delta_strike_kotak_using_websocket(delta, put_or_call):
    """
    No need to pass data frame as it is assumed that dataframe is already present in config
    :param delta: INT -> Delta (1-100)
    :param put_or_call: "p" or "c" -> put or call
    :return: strike price INT
    """
    if len(config.put_option_chain_current) == 0 or len(config.call_option_chain_current) == 0:
        print("No data in option chain!")
        return None
    
    df = config.put_option_chain_current if put_or_call == "p" else config.call_option_chain_current
    # while (True):
    strike = 0
    if (put_or_call == "p"):
        for k, v in df.iterrows():
            OPTION_strike = v["strike"]
            OPTION_DELTA = v['DELTA']
            if (OPTION_DELTA < delta and OPTION_DELTA != 0):
                strike = int(OPTION_strike)
    elif (put_or_call == "c"):
        for k, v in df.iterrows():
            OPTION_strike = v["strike"]
            OPTION_DELTA = v['DELTA']
            if (OPTION_DELTA > delta and OPTION_DELTA != 0):
                strike = int(OPTION_strike)
                return strike
    return strike

def symbol_n_delta_strike_kotak(delta, df, put_or_call):
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
            OPTION_strike = v["strike"]
            # OPTION_strike = int(OPTION_strike[:5])
            # OPTION_LTP=v['last_price']
            OPTION_DELTA = v['DELTA']
            if (OPTION_DELTA < delta and OPTION_DELTA != 0):
                strike = int(OPTION_strike)

    elif (put_or_call == "c"):

        for k, v in df.iterrows():
            OPTION_strike = v["strike"]
            # OPTION_strike = int(OPTION_strike[:5])
            # OPTION_LTP=v['last_price']
            OPTION_DELTA = v['DELTA']
            if (OPTION_DELTA < delta and OPTION_DELTA != 0):
                strike = int(OPTION_strike)
                return strike

    return strike

# Expiry Fucntions
def is_cur_expiry_weekly(expiry_name = "nifty"):  # Returns True for a weekly expiry and False for a monthly expiry
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
    elif expiry_name == 'bankex':
        symbol_expiryday = bankex_expiryday
    elif expiry_name == 'midcap':
        symbol_expiryday = midcap_expiryday
    elif expiry_name == 'finnifty':
        symbol_expiryday = fin_expiryday
    else:
        raise Exception ("Invalid Expiry Name")


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


def put_strike_up_moving_strangle_kotak(diff, putstrike, quantity, product_type, validity, filename, expiry_name="nifty"):
    curtime = dt.datetime.now()
    f = open(filename, "a")  # Append mode
    newstrike = int(putstrike) + diff

    cursymbol = strike_to_symbol_kotak(expiry_name, putstrike, "PUT")
    newsymbol = strike_to_symbol_kotak(expiry_name, newstrike, 'PUT')

    orderid = execute_order_kotak(symbol=cursymbol, type_="BUY", quant=quantity, price=None, trig_price=None,
                                        product=product_type, validity = validity, expiry_name=expiry_name)
    time.sleep(0.5)
    fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
    if fetched_order[0]['ordSt'] == config.success_status_kotak:
        if config.testing_mode:
            executed_price = fetched_order[0]['prc']
        else:
            executed_price = fetched_order[0]['avgPrc']

        f.write(f"{orderid}\tBUY\t{cursymbol}\t{quantity}\t{executed_price}\n")
        set_excel_values(curtime= curtime, pnl_points = 0, delta = config.put_delta_to_sell_at_open, symbol = cursymbol, buy_sell= "BUY", quantity=quantity, price = executed_price)

    else:
        time.sleep(1)
        fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
        if fetched_order[0]['ordSt'] == config.success_status_kotak:
            if config.testing_mode:
                executed_price = fetched_order[0]['prc']
            else:
                executed_price = fetched_order[0]['avgPrc']
            f.write(f"{orderid}\tBUY\t{cursymbol}\t{quantity}\t{executed_price}\n")
            set_excel_values(curtime= curtime, pnl_points = 0, delta = config.put_delta_to_sell_at_open, symbol = cursymbol, buy_sell= "BUY", quantity=quantity, price = executed_price)

        else:
            send_logs("Something Wrong with Order CHeck Now")
            # todo , exit the put position and exit the program


    orderid = execute_order_kotak(symbol=newsymbol, type_="SELL", quant=quantity, price=None, trig_price=None,
                                        product=product_type, validity = validity, expiry_name=expiry_name)
    time.sleep(0.5)
    fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
    if fetched_order[0]['ordSt'] == config.success_status_kotak:
        if config.testing_mode:
            executed_price = fetched_order[0]['prc']
        else:
            executed_price = fetched_order[0]['avgPrc']
        f.write(f"{orderid}\tSELL\t{newsymbol}\t{quantity}\t{executed_price}\n")
        set_excel_values(curtime= curtime, pnl_points = 0, delta = config.put_delta_to_sell_at_open, symbol = newsymbol, buy_sell= "SELL", quantity=quantity, price = executed_price)

    else:
        time.sleep(1)
        fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
        if fetched_order[0]['ordSt'] == config.success_status_kotak:
            if config.testing_mode:
                executed_price = fetched_order[0]['prc']
            else:
                executed_price = fetched_order[0]['avgPrc']
            f.write(f"{orderid}\tSELL\t{newsymbol}\t{quantity}\t{executed_price}\n")
            set_excel_values(curtime= curtime, pnl_points = 0, delta = config.put_delta_to_sell_at_open, symbol = newsymbol, buy_sell= "SELL", quantity=quantity, price = executed_price)

        else:
            send_logs("Something Wrong with Order CHeck Now")
            # todo , exit the put position and exit the program
    f.close()

def put_strike_down_moving_strangle_kotak(diff, putstrike, quantity, product_type, validity, filename, expiry_name="nifty"):
    curtime = dt.datetime.now()
    f = open(filename, "a")  # Append mode
    newstrike = int(putstrike) - diff
    cursymbol = strike_to_symbol_kotak(expiry_name, putstrike, "PUT")
    newsymbol = strike_to_symbol_kotak(expiry_name, newstrike, 'PUT')
    orderid = execute_order_kotak(symbol=cursymbol, type_="BUY", quant=quantity, price=None, trig_price=None,
                                        product=product_type, validity = validity, expiry_name=expiry_name)
    time.sleep(0.5)
    fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
    if fetched_order[0]['ordSt'] == config.success_status_kotak:
        if config.testing_mode:
            executed_price = fetched_order[0]['prc']
        else:
            executed_price = fetched_order[0]['avgPrc']
        f.write(f"{orderid}\tBUY\t{cursymbol}\t{quantity}\t{executed_price}\n")
        set_excel_values(curtime= curtime, pnl_points = 0, delta = config.put_delta_to_sell_at_open, symbol = cursymbol, buy_sell= "BUY", quantity=quantity, price = executed_price)
    else:
        time.sleep(1)
        fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
        if fetched_order[0]['ordSt'] == config.success_status_kotak:
            if config.testing_mode:
                executed_price = fetched_order[0]['prc']
            else:
                executed_price = fetched_order[0]['avgPrc']
            f.write(f"{orderid}\tBUY\t{cursymbol}\t{quantity}\t{executed_price}\n")
            set_excel_values(curtime= curtime, pnl_points = 0, delta = config.put_delta_to_sell_at_open, symbol = cursymbol, buy_sell= "BUY", quantity=quantity, price = executed_price)

        else:
            send_logs("Something Wrong with Order CHeck Now")
            # todo , exit the put position and exit the program


    orderid = execute_order_kotak(symbol=newsymbol, type_="SELL", quant=quantity, price=None, trig_price=None,
                                        product=product_type, validity = validity, expiry_name=expiry_name)
    time.sleep(0.5)
    fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
    if fetched_order[0]['ordSt'] == config.success_status_kotak:
        if config.testing_mode:
            executed_price = fetched_order[0]['prc']
        else:
            executed_price = fetched_order[0]['avgPrc']
        f.write(f"{orderid}\tSELL\t{newsymbol}\t{quantity}\t{executed_price}\n")
        set_excel_values(curtime= curtime, pnl_points = 0, delta = config.put_delta_to_sell_at_open, symbol = newsymbol, buy_sell= "SELL", quantity=quantity, price = executed_price)
    else:
        time.sleep(1)
        fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
        if fetched_order[0]['ordSt'] == config.success_status_kotak:
            if config.testing_mode:
                executed_price = fetched_order[0]['prc']
            else:
                executed_price = fetched_order[0]['avgPrc']
            f.write(f"{orderid}\tSELL\t{newsymbol}\t{quantity}\t{executed_price}\n")
            set_excel_values(curtime= curtime, pnl_points = 0, delta = config.put_delta_to_sell_at_open, symbol = newsymbol, buy_sell= "SELL", quantity=quantity, price = executed_price)

        else:
            send_logs("Something Wrong with Order CHeck Now")
            # todo , exit the put position and exit the program
    f.close()

def call_strike_down_moving_strangle_kotak(diff, callstrike, quantity, product_type, validity, filename, expiry_name="nifty"):
    curtime = dt.datetime.now()
    f = open(filename, "a")  # Append mode
    newstrike = int(callstrike) - diff
    cursymbol = strike_to_symbol_kotak(expiry_name, callstrike, "CALL")
    newsymbol = strike_to_symbol_kotak(expiry_name, newstrike, 'CALL')
    orderid = execute_order_kotak(symbol=cursymbol, type_="BUY", quant=quantity, price=None, trig_price=None,
                                        product=product_type, validity = validity,  expiry_name=expiry_name)
    time.sleep(0.5)
    fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
    if fetched_order[0]['ordSt'] == config.success_status_kotak:
        if config.testing_mode:
            executed_price = fetched_order[0]['prc']
        else:
            executed_price = fetched_order[0]['avgPrc']
        f.write(f"{orderid}\tBUY\t{cursymbol}\t{quantity}\t{executed_price}\n")
        set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = cursymbol, buy_sell= "BUY", quantity=quantity, price = executed_price)
    else:
        time.sleep(1)
        fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
        if fetched_order[0]['ordSt'] == config.success_status_kotak:
            if config.testing_mode:
                executed_price = fetched_order[0]['prc']
            else:
                executed_price = fetched_order[0]['avgPrc']
            f.write(f"{orderid}\tBUY\t{cursymbol}\t{quantity}\t{executed_price}\n")
            set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = cursymbol, buy_sell= "BUY", quantity=quantity, price = executed_price)

        else:
            send_logs("Something Wrong with Order CHeck Now")
            # todo , exit the put position and exit the program


    orderid = execute_order_kotak(symbol=newsymbol, type_="SELL", quant=quantity, price=None, trig_price=None,
                                        product=product_type, validity = validity, expiry_name=expiry_name)
    time.sleep(0.5)
    fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
    if fetched_order[0]['ordSt'] == config.success_status_kotak:
        if config.testing_mode:
            executed_price = fetched_order[0]['prc']
        else:
            executed_price = fetched_order[0]['avgPrc']
        f.write(f"{orderid}\tSELL\t{newsymbol}\t{quantity}\t{executed_price}\n")
        set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = newsymbol, buy_sell= "SELL", quantity=quantity, price = executed_price)
    else:
        time.sleep(1)
        fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
        if fetched_order[0]['ordSt'] == config.success_status_kotak:
            if config.testing_mode:
                executed_price = fetched_order[0]['prc']
            else:
                executed_price = fetched_order[0]['avgPrc']
            f.write(f"{orderid}\tSELL\t{newsymbol}\t{quantity}\t{executed_price}\n")
            set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = newsymbol, buy_sell= "SELL", quantity=quantity, price = executed_price)
        else:
            send_logs("Something Wrong with Order CHeck Now")
            # todo , exit the put position and exit the program
    f.close()

def call_strike_up_moving_strangle_kotak(diff, callstrike, quantity, product_type, validity, filename, expiry_name="nifty"):
    curtime = dt.datetime.now()
    f = open(filename, "a")  # Append mode
    newstrike = int(callstrike) + diff
    cursymbol = strike_to_symbol_kotak(expiry_name, callstrike, "CALL")
    newsymbol = strike_to_symbol_kotak(expiry_name, newstrike, 'CALL')

    orderid = execute_order_kotak(symbol=cursymbol, type_="BUY", quant=quantity, price=None, trig_price=None,
                                        product=product_type, validity = validity, expiry_name=expiry_name)
    time.sleep(0.5)
    fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
    if fetched_order[0]['ordSt'] == config.success_status_kotak:
        if config.testing_mode:
            executed_price = fetched_order[0]['prc']
        else:
            executed_price = fetched_order[0]['avgPrc']
        f.write(f"{orderid}\tBUY\t{cursymbol}\t{quantity}\t{executed_price}\n")
        set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = cursymbol, buy_sell= "BUY", quantity=quantity, price = executed_price)
    else:
        time.sleep(1)
        fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
        if fetched_order[0]['ordSt'] == config.success_status_kotak:
            if config.testing_mode:
                executed_price = fetched_order[0]['prc']
            else:
                executed_price = fetched_order[0]['avgPrc']
            f.write(f"{orderid}\tBUY\t{cursymbol}\t{quantity}\t{executed_price}\n")
            set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = cursymbol, buy_sell= "BUY", quantity=quantity, price = executed_price)

        else:
            send_logs("Something Wrong with Order CHeck Now")
            # todo , exit the put position and exit the program


    orderid = execute_order_kotak(symbol=newsymbol, type_="SELL", quant=quantity, price=None, trig_price=None,
                                        product=product_type, validity = validity, expiry_name=expiry_name)
    time.sleep(0.5)
    fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
    if fetched_order[0]['ordSt'] == config.success_status_kotak:
        if config.testing_mode:
            executed_price = fetched_order[0]['prc']
        else:
            executed_price = fetched_order[0]['avgPrc']
        f.write(f"{orderid}\tSELL\t{newsymbol}\t{quantity}\t{executed_price}\n")
        set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = newsymbol, buy_sell= "SELL", quantity=quantity, price = executed_price)
    else:
        time.sleep(1)
        fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
        if fetched_order[0]['ordSt'] == config.success_status_kotak:
            if config.testing_mode:
                executed_price = fetched_order[0]['prc']
            else:
                executed_price = fetched_order[0]['avgPrc']
            f.write(f"{orderid}\tSELL\t{newsymbol}\t{quantity}\t{executed_price}\n")
            set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = newsymbol, buy_sell= "SELL", quantity=quantity, price = executed_price)

        else:
            send_logs("Something Wrong with Order CHeck Now")
            # todo , exit the put position and exit the program
    f.close()

def monitor_symbol_1230_strategy_strangle_kotak(filename,  expiry_name):
    
    global order_index, txn_type_index, symbol_index, quantity_index, price_index
    callsymbol = ""
    putsymbol = ""
    curtime = dt.datetime.now()
    cur_hour = curtime.hour
    curdate = dt.datetime.today()
    curday = curdate.weekday()
    
    f = open(filename, "r")  # Append mode
    filedata = f.read()
    f.close()
    order_data = filedata.splitlines()
    num_orders = len(order_data)
    processed_order_data = []

    for i in range(num_orders):  # Processes Data fetched from file and stores it as a 2D array in processed_order_data
        processed_order_data.append(order_data[i].split('\t'))

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

    for symbol in symbol_dict:
        quantity = symbol_dict[symbol][0]
        try:
            symbol_dict[symbol][2] = (symbol_dict[symbol][1] * -1) + (
                    quantity * last_price_kotak(symbol, expiry_name))  # symbolpnl = BuySellValue+ (Quantity*LTP)
        except Exception as e:
            time.sleep(0.5)
            symbol_dict[symbol][2] = (symbol_dict[symbol][1] * -1) + (
                    quantity * last_price_kotak(symbol, expiry_name))  # symbolpnl = BuySellValue+ (Quantity*LTP)
        time.sleep(0.2)
        pnl += symbol_dict[symbol][2]

        # todo check for each expiry
        instrument_type = symbol[-2:]
        if quantity < 0 and (instrument_type == 'P' or instrument_type == 'PE'):
            putsymbol = symbol
            putquantity = int(quantity)
            send_logs("Put symbol is " + putsymbol + " and quantity is " + str(putquantity))
        elif quantity < 0 and (instrument_type == 'C' or instrument_type == 'CE'):
            callsymbol = symbol
            callquantity = int(quantity)
            send_logs("Call symbol is " + callsymbol + " and quantity is " + str(callquantity))
            
            
    
    
def monitor_symbol_moving_strangle_with_delta_multiple_kotak(product_type, call_diff, put_diff, validity,
                                                                filename, expiry_name="nifty"):
    global order_index, txn_type_index, symbol_index, quantity_index, price_index
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

    for symbol in symbol_dict:
        quantity = symbol_dict[symbol][0]
        try:
            symbol_dict[symbol][2] = (symbol_dict[symbol][1] * -1) + (
                    quantity * last_price_kotak(symbol, expiry_name))  # symbolpnl = BuySellValue+ (Quantity*LTP)
        except Exception as e:
            time.sleep(0.5)
            symbol_dict[symbol][2] = (symbol_dict[symbol][1] * -1) + (
                    quantity * last_price_kotak(symbol, expiry_name))  # symbolpnl = BuySellValue+ (Quantity*LTP)
        time.sleep(0.2)
        pnl += symbol_dict[symbol][2]

        # todo check for each expiry
        instrument_type = symbol[-2:]
        if quantity < 0 and (instrument_type == 'P' or instrument_type == 'PE'):
            putsymbol = symbol
            putquantity = int(quantity)
            send_logs("Put symbol is " + putsymbol + " and quantity is " + str(putquantity))
        elif quantity < 0 and (instrument_type == 'C' or instrument_type == 'CE'):
            callsymbol = symbol
            callquantity = int(quantity)
            send_logs("Call symbol is " + callsymbol + " and quantity is " + str(callquantity))

    # is_weekly_expiry = is_cur_expiry_weekly(expiry_name)

    # diff_plus = config.diff_plus
    # diff_minus = config.diff_minus
    
    call_max_range = call_diff + config.call_diff_plus
    call_min_range = call_diff - config.call_diff_minus
    put_max_range = put_diff + config.put_diff_plus
    put_min_range = put_diff - config.put_diff_minus
    
    # symbol_cur_price = float(msf.get_ltp_for_index_using_kotak(expiry_name))

    symbol_cur_price = float(weekly_future_using_kotak(expiry_name))
    time.sleep(0.2)
    send_logs(f"CURRENTLY {expiry_name} IS AT: " + str(symbol_cur_price))

    strike_adjustment = config.strike_adjustment

   

    if (callsymbol == "" and putsymbol == ""):
        send_logs("PLEASE TAKE SOME POSITIONS")
        return 0.0

    else:
        callstrike = int(symbol_to_strike_kotak(callsymbol, expiry_name))
        putstrike = int(symbol_to_strike_kotak(putsymbol, expiry_name))

        put_diff = symbol_cur_price - putstrike
        call_diff = callstrike - symbol_cur_price

        if put_diff < put_max_range and put_diff > put_min_range:
            send_logs(f"Put Diff is in range, no action needed!!! Put_Min_Range: {put_min_range} < PutDiff: {put_diff} < Put_max_range: {put_max_range}")


        send_logs(f"Put_max_range: {put_max_range} Put_Min_Range: {put_min_range} PutDiff: {put_diff}")
        send_logs(f"Call_max_range: {call_max_range} Call_Min_Range: {call_min_range} CallDiff: {call_diff}")
        
        if put_diff > put_max_range or config.testing_mode:
            # time.sleep(5)
            send_logs("Put Strike Diff is " + str(put_diff) + " Moving Puts Up")
            # diff, putstrike, quantity, product_type, validity, filename, expiry_name="nifty"
            put_strike_up_moving_strangle_kotak(diff=strike_adjustment,  putstrike = putstrike, quantity = abs(putquantity), product_type= product_type, validity = validity,
                                                      filename = filename, expiry_name = expiry_name)
        elif put_diff < put_min_range:
            # time.sleep(5)
            send_logs("Put Strike Diff is " + str(put_diff) + " Moving Puts Down")
            put_strike_down_moving_strangle_kotak(diff = strike_adjustment, putstrike= putstrike, quantity= abs(putquantity), product_type= product_type, validity = validity,
                                                      filename = filename, expiry_name = expiry_name)
        else:
            send_logs("Put Strike Diff is " + str(put_diff) + " Nothing to do right now !!")
            send_logs("Will Move Puts Up At " + str(putstrike + put_max_range))
            send_logs("Will Move Puts Down At " + str(putstrike + put_min_range))

        if call_diff > call_max_range or config.testing_mode :
            # time.sleep(5)
            send_logs("Call Strike Diff is " + str(call_diff) + " Moving Calls Down")
            call_strike_down_moving_strangle_kotak(diff = strike_adjustment, callstrike= callstrike, quantity = abs(callquantity), product_type= product_type, validity = validity,
                                                      filename = filename, expiry_name = expiry_name)
        elif call_diff < call_min_range:
            # time.sleep(5)
            send_logs("Call Strike Diff is " + str(call_diff) + " Moving Calls Up")
            call_strike_up_moving_strangle_kotak(diff = strike_adjustment, callstrike= callstrike, quantity = abs(callquantity), product_type= product_type, validity = validity,
                                                      filename = filename, expiry_name = expiry_name)
        else:
            send_logs("Call Strike Diff is " + str(call_diff) + " Nothing to do right now !!")
            send_logs("Will Move Calls Up At " + str(callstrike - call_min_range))
            send_logs("Will Move Calls Down At " + str(callstrike - call_max_range))

    return round(pnl, 1)


def exit_all_positions_from_algo_kotak(product_type, validity, filename, expiry_name="nifty"):
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
            send_logs(f"Exiting {symbol}")
            curtime = dt.datetime.now()
            orderid = execute_order_kotak(symbol = symbol, type_ = "BUY", quant = -1*quantity, price = None, trig_price =  None,
                                                product= product_type , validity=validity, expiry_name= expiry_name)
            fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
            if fetched_order[0]['ordSt'] == config.success_status_kotak:
                if config.testing_mode:
                    executed_price = fetched_order[0]['prc']
                else:
                    executed_price = fetched_order[0]['avgPrc']
                f.write(f"{orderid}\tSELL\t{symbol}\t{-1*quantity}\t{executed_price}\n")
                set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = symbol, buy_sell= "BUY", quantity=-1*quantity, price = executed_price)
            else:
                time.sleep(1)
                fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
                if fetched_order[0]['ordSt'] == config.success_status_kotak:
                    if config.testing_mode:
                        executed_price = fetched_order[0]['prc']
                    else:
                        executed_price = fetched_order[0]['avgPrc']
                    f.write(f"{orderid}\tSELL\t{symbol}\t{-1*quantity}\t{executed_price}\n")
                    set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = symbol, buy_sell= "BUY", quantity=-1*quantity, price = executed_price)
                else:
                    send_logs("Something Wrong with Order CHeck Now")
                    # todo , exit the put position and exit the program
                    break


    for symbol in symbol_dict:  # Exit Buy Positions
        quantity = symbol_dict[symbol][0]
        if quantity > 0:
            send_logs("Exiting ", symbol)
            curtime = dt.datetime.now()
            orderid = execute_order_kotak(symbol = symbol, type_ = "SELL", quant = quantity, price = None, trig_price =  None,
                                                product= product_type , validity=validity, expiry_name= expiry_name)
            fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
            if fetched_order[0]['ordSt'] == config.success_status_kotak:
                if config.testing_mode:
                    executed_price = fetched_order[0]['prc']
                else:
                    executed_price = fetched_order[0]['avgPrc']
                f.write(f"{orderid}\tSELL\t{symbol}\t{quantity}\t{executed_price}\n")
                set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = symbol, buy_sell= "SELL", quantity=quantity, price = executed_price)
            else:
                time.sleep(1)
                fetched_order = config.NEO_OBJ.order_history(order_id = orderid)['data']['data']
                if fetched_order[0]['ordSt'] == config.success_status_kotak:
                    if config.testing_mode:
                        executed_price = fetched_order[0]['prc']
                    else:
                        executed_price = fetched_order[0]['avgPrc']
                    f.write(f"{orderid}\tSELL\t{symbol}\t{quantity}\t{executed_price}\n")
                    set_excel_values(curtime= curtime, pnl_points = 0, delta = config.call_delta_to_sell_at_open, symbol = symbol, buy_sell= "SELL", quantity=quantity, price = executed_price)
                else:
                    send_logs("Something Wrong with Order CHeck Now")
                    # todo , exit the put position and exit the program

    f.close()