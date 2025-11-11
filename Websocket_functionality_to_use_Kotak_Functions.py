from logger_moving_strangle import logger
import datetime as dt
import config_moving_strangle_websocket as config
from datetime import datetime
from dateutil.relativedelta import relativedelta
import threading
from time import sleep
from neo_api_client import NeoAPI
import pandas as pd
import numpy as np
import os
import logging
import sys
import shutil
import xlwings as xw
import time
import moving_strangle_functions_websocket as msf
import warnings
warnings.filterwarnings("ignore")
import pickle
def on_order_error(error_message=None):
    logger.info(f'Error from Order websocket  {error_message}')

def on_error(message):
    result = message
    print(f"OnError: {result}")

def on_close(message):
    print(f"OnClose: {message}")

def on_message(message):
    symbol_name = ""
    if config.stop_thread:
        return
    # print("Received message: (message}")
    for i in message:
        # print(i)
        try:
            tk = i['tk']
            symbol_name = config.map_instrumenttoken_symbol_name[tk]
            ltp = i['ltp'] # sometimes ltp is not there, so we handle it by checking if ltp is there or not
            
            config.datafeed[symbol_name] = i # raw message passed to datafeed
            # config.datafeed[i['tk']] = float(i['ltp'])
        except Exception as e:
            pass
        
        
def login():
    client = NeoAPI(consumer_key=config.CONSUMER_KEY, consumer_secret=config.API_SECRET,
                    environment='prod', on_message=on_message, on_error=on_error, on_close=on_close, on_open=None)

    client.login(mobilenumber=config.MOBILE, password=config.PASSWORD)
    sesRes = client.session_2fa(OTP=str(config.MPIN))
    # logger.info(f'{sesRes}')
    # threading.Thread(target = client.subscribe_to_orderfeed).start()
    return client

def send_logs(message, log_type='info'):
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

def initializer(expiry_name):
    send_logs(f"CLIENT NAME IS : {config.client_name}")
    send_logs(f"Testing Mode ? : {config.testing_mode}")
    send_logs(f"Expiry Name : {expiry_name}")
    
    td = dt.datetime.now().strftime('%d_%m_%Y')
    msf.create_file_structure_ifnotexists(f'data\\{td}\\')
    if os.path.exists(f'data\\{td}\\neo_obj.pkl'):
        print("No login required, already existing login object!")
        with open(f'data\\{td}\\neo_obj.pkl', 'rb') as f:
            config.NEO_OBJ = pickle.load(f)
    else:
        config.NEO_OBJ: NeoAPI = login()
        print("Fresh login object created!")
        with open(f'data\\{td}\\neo_obj.pkl', 'wb') as f:
            pickle.dump(config.NEO_OBJ, f)
    # send_logs(config.NEO_OBJ)

    if expiry_name == 'sensex' or expiry_name == "bankex":
        cashUrl = config.NEO_OBJ.scrip_master(exchange_segment='BSE')
        optionUrl = config.NEO_OBJ.scrip_master(exchange_segment='BFO')
    else:
        cashUrl = config.NEO_OBJ.scrip_master(exchange_segment='NSE')
        optionUrl = config.NEO_OBJ.scrip_master(exchange_segment='NFO')
    optionDF = None
    cashDF = None
    dtime = dt.datetime.now().strftime('%d_%m_%Y')
    data_path = f"C:\\Users\\ashis\\OneDrive\\Desktop\\run_sheet_code_folder\\kotak_Neo_Codes\\data\\{dtime}\\"
    msf.create_file_structure_ifnotexists(data_path)
    option_csv_path = os.path.join(data_path, f'{expiry_name}_option_data.csv')

    cash_csv_path = os.path.join(data_path, f'{expiry_name}_cash.csv')

    if os.path.exists(option_csv_path) and os.path.exists(cash_csv_path):
        optionDF = pd.read_csv(option_csv_path)
        cashDF = pd.read_csv(cash_csv_path)
    else:
        optionDF = pd.read_csv(optionUrl)
        cashDF = pd.read_csv(cashUrl)
        optionDF.to_csv(option_csv_path, index=False)
        cashDF.to_csv(cash_csv_path, index=False)

    if expiry_name == 'sensex':
        config.pSymbolName = config.SENSEX_P_SYMBOL_NAME
        config.pInstType = config.SENSEX_INST_TYPE_INDEX_OPTION
    elif expiry_name == "bankex":
        config.pSymbolName = config.BANKEX_P_SYMBOL_NAME
        config.pInstType = config.BANKEX_INST_TYPE_INDEX_OPTION
    elif expiry_name == 'nifty':
        config.pSymbolName = config.NIFTY_SYMBOL
        config.pInstType = config.NIFTY_INST_TYPE_INDEX_OPTION
    elif expiry_name == 'banknifty':
        config.pSymbolName = config.BANKNIFTY_SYMBOL
        config.pInstType = config.NIFTY_INST_TYPE_INDEX_OPTION
    elif expiry_name == 'midcap':
        config.pSymbolName = config.MIDCAP_SYMBOL
        config.pInstType = config.NIFTY_INST_TYPE_INDEX_OPTION
    elif expiry_name == 'finnifty':
        config.pSymbolName = config.FINNIFTY_SYMBOL
        config.pInstType = config.NIFTY_INST_TYPE_INDEX_OPTION
    else:
        raise Exception('Invalid expiry name')
    config.TOKEN_MAP = optionDF
    config.SPOT_TOKEN = cashDF

def stream(instrument_tokens):
    
    print("Stream function started")
    try:
        client = config.NEO_OBJ
        client.subscribe(instrument_tokens, isIndex = False, isDepth = False)
    except Exception as e:
        send_logs(f"Error in subscribing to datafeed {e}")
        return False
    print("Stream function finished")
   
   
def subscribe_to_option_datafeed_optionchain(depth = 25):
    
    expiry_name = config.expiry_name
    map_instrumenttoken_symbol_name = {}
    a,b = msf.get_exchange_segment(expiry_name)
    map_instrumenttoken_symbol_name[str(a)] = config.expiry_name
    
    client = config.NEO_OBJ
    details = msf.get_details_for_expiry(expiry_name)
    diff_between_two_strikes = details['difference_between_strikes']
    # diff_between_two_strikes = 50

    symbol_cur_price = float(msf.get_ltp_for_index_using_kotak(expiry_name))

    nearer_strike = symbol_cur_price / diff_between_two_strikes
    mod = symbol_cur_price % diff_between_two_strikes
    if mod > diff_between_two_strikes / 2:
        nearer_strike = (int(nearer_strike) + 1) * diff_between_two_strikes
    else:
        nearer_strike = (int(nearer_strike)) * diff_between_two_strikes

    atm_call_symbol_kotak  = msf.strike_to_symbol_kotak(expiry_name, nearer_strike, "CALL")
    atm_put_symbol_kotak = msf.strike_to_symbol_kotak(expiry_name, nearer_strike, "PUT")

    # based on depth and difference between two strikes, get strikes for watchlist
    strikes = [strike for strike in range(nearer_strike - depth * diff_between_two_strikes, nearer_strike + depth * diff_between_two_strikes, diff_between_two_strikes)]
    call_instrument_tokens = []
    put_instrument_tokens = []

    call_symbol_to_strike_map = {}
    put_symbol_to_strike_map = {}
    for strike in strikes:
        call_symbol_kotak  = msf.strike_to_symbol_kotak(expiry_name, strike, "CALL")
        put_symbol_kotak = msf.strike_to_symbol_kotak(expiry_name, strike, "PUT")
        call_symbol_to_strike_map[call_symbol_kotak] = strike
        put_symbol_to_strike_map[put_symbol_kotak] = strike
        
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
        map_instrumenttoken_symbol_name[str(symbol_token)] = call_symbol_kotak
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
        map_instrumenttoken_symbol_name[str(symbol_token)] = put_symbol_kotak
    
    # for option_chain_data
    config.call_symbol_to_strike_map = call_symbol_to_strike_map
    config.put_symbol_to_strike_map = put_symbol_to_strike_map
    
    config.map_instrumenttoken_symbol_name = map_instrumenttoken_symbol_name
    instrument_tokens_all = [{"instrument_token": str(a), "exchange_segment": str(b)}] + call_instrument_tokens + put_instrument_tokens 
    threading.Thread(target=client.subscribe, args=(instrument_tokens_all,)).start()
    

def moving_strangle_strategy():
    
    subscribe_to_option_datafeed_optionchain(25)
    time.sleep(5)
    
    curtime, cur_minute, cur_hour, curdate = msf.get_current_time()
    send_logs(f'Current Time {curtime}')
    start = 1
    td = datetime.today().date()
    td = td.strftime("%Y-%m-%d")
    
    if config.testing_mode:
        datafiles_base_path = ("C:\\Users\\ashis\\OneDrive\\Desktop\\moving_strangle_strategy\\datafiles"
                               f"\\testing\\{config.expiry_name}_moving_strangle\\{td}\\")
    else:
        datafiles_base_path = ("C:\\Users\\ashis\\OneDrive\\Desktop\\moving_strangle_strategy\\datafiles"
                               f"\\{config.expiry_name}_moving_strangle\\{td}\\")

    msf.create_file_structure_ifnotexists(datafiles_base_path)
    filename = datafiles_base_path + f"_{config.expiry_name}_moving_strangle.txt"
    # delete filename if exists
    if config.delete_datafiles == True:
        if os.path.exists(filename):
            os.remove(filename)
            
        if os.path.exists(datafiles_base_path + "index_price_at_sell.txt"):
            os.remove(datafiles_base_path + "index_price_at_sell.txt")
                

    f = open(filename, "a")  # Append mode
    f.close()
    f = open(filename, "r")  # File Reading
    firstline_data = f.readline()
    f.close()
    expiry_details = msf.get_details_for_expiry(config.expiry_name)

    # config.sheet = msf.excel_initialisation(datafiles_base_path, config.expiry_name)

    
    RUN_STRADDLE = config.RUN_STRADDLE
    # kotak_testing_mode = False
    # lot size 10

    lot_size = expiry_details['lot_size']
    lots_to_trade = config.lots_to_trade

    quantity = int(lot_size * lots_to_trade)
    # MaxLoss = config.max_loss  # 1% with hedges 30 point sl
    # iterator = 0
    
    if os.path.exists(datafiles_base_path + "index_price_at_sell.txt"):
        config.index_price_at_sell = float(open(datafiles_base_path + "index_price_at_sell.txt", "r").read())
        
    start_hour = config.start_hour
    start_minute = config.start_minute
    start_seconds = config.start_second

    end_hour = config.end_hour
    end_minute = config.end_minute

    call_delta_to_sell_at_open = config.call_delta_to_sell_at_open  # set it from 1 to 50. default 15
    put_delta_to_sell_at_open = config.put_delta_to_sell_at_open  # set it from 1 to 50. default 15

    if firstline_data == '':  # Empty File
        send_logs("Order File Empty")
    else:
        firstline_data_list = firstline_data.split('\t')
        # logger.info(firstline_data_list)
        quantity = abs(int(firstline_data_list[3]))
        send_logs(f"Quantity Fetched from file is {quantity}")
    diff_between_two_strikes = expiry_details['difference_between_strikes']
    
    symbol_strike = msf.weekly_future_using_kotak_using_websocket()
    strike_symbol = symbol_strike / diff_between_two_strikes
    mod = symbol_strike % diff_between_two_strikes
    if mod > diff_between_two_strikes / 2:
        strike_symbol = (int(strike_symbol) + 1) * diff_between_two_strikes
    else:
        strike_symbol = (int(strike_symbol)) * diff_between_two_strikes  

    # sets call and put ooption chain in config.call_option_chain_current and config.put_option_chain_current
    msf.COMPLETE_OPTION_CHAIN_KOTAK_USING_WEBSOCKET(config.option_chain_depth)
    delta_n_call = msf.symbol_n_delta_strike_kotak_using_websocket(call_delta_to_sell_at_open, 'c')
    delta_n_put = msf.symbol_n_delta_strike_kotak_using_websocket(put_delta_to_sell_at_open, 'p')
    flag = 0
    # test_flag = 1
    if config.start_asap:
        cur_hour, cur_minute, cur_seconds = dt.datetime.now().hour, dt.datetime.now().minute, dt.datetime.now().second
        start_hour = cur_hour
        start_minute = cur_minute
        start_seconds = cur_seconds
        
        
    max_profit_points_until_now = 0
    
    while flag != 1:
        curtime = dt.datetime.now()
        cur_seconds = curtime.second
        cur_minute = curtime.minute
        cur_hour = curtime.hour
        curdate = dt.datetime.today()

        order_details_for_excel = []

        # send_logs("Time is " + str(curtime))
        
        if (cur_hour == start_hour and cur_minute == start_minute and cur_seconds > start_seconds and start == 1) or (
                config.testing_mode and start == 1):
            symbol_strike = msf.weekly_future_using_kotak_using_websocket()
            strike_symbol = symbol_strike / diff_between_two_strikes
            mod = symbol_strike % diff_between_two_strikes
            if mod > diff_between_two_strikes / 2:
                strike_symbol = (int(strike_symbol) + 1) * diff_between_two_strikes
            else:
                strike_symbol = (int(strike_symbol)) * diff_between_two_strikes  

            # sets call and put ooption chain in config.call_option_chain_current and config.put_option_chain_current
            msf.COMPLETE_OPTION_CHAIN_KOTAK_USING_WEBSOCKET(config.option_chain_depth)
            delta_n_call = msf.symbol_n_delta_strike_kotak_using_websocket(call_delta_to_sell_at_open, 'c')
            delta_n_put = msf.symbol_n_delta_strike_kotak_using_websocket(put_delta_to_sell_at_open, 'p')
            PUT_NIFTY_OPTION_CHAIN_df = config.put_option_chain_current
            CALL_NIFTY_OPTION_CHAIN_df = config.call_option_chain_current
            ###################################### HEDGING  ############################################
            if config.enable_hedging:
                hedge_delta_n_call = strike_symbol + config.call_hedge_distance
                hedge_delta_n_put = strike_symbol - config.put_hedge_distance
                hedge_putsymbol = str(
                    PUT_NIFTY_OPTION_CHAIN_df.loc[PUT_NIFTY_OPTION_CHAIN_df['strike'] == hedge_delta_n_put][
                        'symbol'].values[0])
                
                hedge_callsymbol = str(
                    CALL_NIFTY_OPTION_CHAIN_df.loc[
                        CALL_NIFTY_OPTION_CHAIN_df['strike'] == hedge_delta_n_call]['symbol'].values[0])
                
                status = msf.execute_order_kotak_using_websocket(symbol=hedge_putsymbol, type_="BUY", quant=quantity, price=None,
                                                trig_price=None, filename = filename, write_to_file = False)

                
                if status == None:
                    send_logs("Order not executed. Exiting")
                    # TODO - SELL ALL OPEN POSITIONS 
                    break
                status = msf.execute_order_kotak_using_websocket(symbol=hedge_callsymbol, type_="BUY", quant=quantity, price=None,
                                                    trig_price=None, filename = filename, write_to_file = False)
                if status == None:
                    send_logs("Order not executed. Exiting")
                    # TODO - SELL ALL OPEN POSITIONS 
                    break
            ###################################### HEDGING  ############################################
            call_price_sold = 0
            put_price_sold = 0
            if RUN_STRADDLE:
                putsymbol = str(PUT_NIFTY_OPTION_CHAIN_df.loc[
                                    PUT_NIFTY_OPTION_CHAIN_df['strike'] == strike_symbol]['symbol'].values[0])
                callsymbol = str(
                    CALL_NIFTY_OPTION_CHAIN_df.loc[
                        CALL_NIFTY_OPTION_CHAIN_df['strike'] == strike_symbol]['symbol'].values[0])
            else:
                putsymbol = str(
                    PUT_NIFTY_OPTION_CHAIN_df.loc[PUT_NIFTY_OPTION_CHAIN_df['strike'] == delta_n_put][
                        'symbol'].values[0])
                callsymbol = str(
                    CALL_NIFTY_OPTION_CHAIN_df.loc[
                        CALL_NIFTY_OPTION_CHAIN_df['strike'] == delta_n_call]['symbol'].values[0])

            # execute_order_kotak(nifty_symbol, "SELL", 1, None, None, "NRML","DAY", "nifty")
            # symbol, type_, quant, price, trig_price, product, validity, expiry_name
            put_executed_price = msf.execute_order_kotak_using_websocket(symbol=putsymbol, type_="SELL", quant=quantity, price=None,
                                               trig_price=None, filename = filename)
            if put_executed_price == None:
                send_logs("Order not executed. Exiting")
                # TODO - SELL ALL OPEN POSITIONS 
                break
            put_price_sold = put_executed_price
                    
            call_executed_price = msf.execute_order_kotak_using_websocket(symbol=callsymbol, type_="SELL", quant=quantity, price=None,
                                                trig_price=None, filename = filename)
            if call_executed_price == None:
                send_logs("Order not executed. Exiting")
                # TODO - SELL ALL OPEN POSITIONS 
                break
            
            # config.index_price_at_sell = msf.get_ltp_for_symbol_from_datafeed_using_websocket(config.expiry_name)
            # write index_price_at_sell to a file in data folder
            
            # save_index_price = open(datafiles_base_path + "index_price_at_sell.txt", "w")
            # save_index_price.write(str(config.index_price_at_sell))
            # save_index_price.close()
            
            call_price_sold = call_executed_price        
            if config.smart_max_loss_pts:
                config.max_loss_pts = round((call_price_sold + put_price_sold), 2)
                
            start = 0

        elif (cur_hour < start_hour or (cur_hour == start_hour and cur_minute < start_minute)
              or (cur_hour == start_hour and cur_minute == start_minute and cur_seconds <= start_seconds)):
            send_logs("Waiting for Start Time. Current Time is " + str(curtime))
            time.sleep(1)
            continue
        
        try:
            # send_logs("Max loss in points is: " + str(MaxLoss / quantity))
            curtime = dt.datetime.now()
            cur_minute = curtime.minute
            cur_hour = curtime.hour
            curdate = dt.datetime.today()
            
            
            if config.delete_datafiles == False and config.start_asap == False:
                # subscribe_to_option_datafeed(callsymbol, putsymbol)
                subscribe_to_option_datafeed_optionchain(25)
                # time to let streaming start
                time.sleep(4)  
            msf.COMPLETE_OPTION_CHAIN_KOTAK_USING_WEBSOCKET(config.option_chain_depth)
            call_iv, put_iv = msf.get_atm_iv_using_websocket()
            print(f"Time {curtime} : Call IV is {call_iv} and Put IV is {put_iv} and IV sum is {call_iv + put_iv}") 
            if os.path.exists(datafiles_base_path + "index_price_at_sell.txt") and config.index_price_at_sell == None:
                config.index_price_at_sell = float(open(datafiles_base_path + "index_price_at_sell.txt", "r").read())
            
            status  = msf.monitor_positions_kotak_using_websocket(filename)
            if status == None:
                send_logs("Error in monitoring positions")
                break
            details = msf.get_details_for_expiry(config.expiry_name)
            lot_size = details['lot_size']
            open_positions, close_positions , profit = msf.read_positions_file_using_websocket(filename)
            print(f"Time {curtime} : Running Profit is {profit}")
            time.sleep(0.2)
            if len(open_positions) == 0:
                send_logs("No Open Positions. Exiting")
                msf.exit_all_open_positions_kotak_using_websocket(filename)
                break
            if profit < -1*config.max_loss_pts:
                send_logs("Max Loss Hit. Exiting")
                msf.exit_all_open_positions_kotak_using_websocket(filename)
                break
            elif profit > config.target_profit_pts:
                send_logs("Target Profit Hit. Exiting")
                msf.exit_all_open_positions_kotak_using_websocket(filename)
                break
            
            # add trailing stop loss
            
            
        except Exception as e:
            send_logs("________________________________________________________________________________")
            send_logs("Error occured. Check what's wrong urgently..............")
            send_logs(e)
            time.sleep(5)
expiry_name = config.expiry_name
msf.initialize_logger(expiry_name)
logger.info(f'Expiry Name {expiry_name}')
# startTime = dt.datetime.now(config.TIME_ZONE)
# closingTime = startTime.replace(hour=9, minute=15, second=0, microsecond=0)
# interval = max(0, (closingTime - startTime).total_seconds())
# logger.info(f'System will Start after  {interval} sec')
# sleep(interval)
initializer(expiry_name)
print("initialised...")
# greek_indicator()
moving_strangle_strategy()