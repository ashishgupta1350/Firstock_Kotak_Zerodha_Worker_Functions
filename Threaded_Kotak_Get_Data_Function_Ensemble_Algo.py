import time
import threading
import logging
import random
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# --- Logging Setup ---
# Set up logging to see output from different threads clearly
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)

# --- Mock Objects and Functions ---
# These are dummy versions of your external dependencies so the example can run.
# In your real app, you would import your actual modules.

class MockNeoObj:
    """Mocks the config.NEO_OBJ for API calls."""
    def execute_order_kotak_using_websocket(self, **kwargs):
        """Mocks order execution."""
        logging.info(f"Mock execute_order for: {kwargs.get('symbol')}")
        time.sleep(0.1)  # Simulate network delay
        return f"order_{random.randint(1000, 9999)}"

    def order_history(self, order_id):
        """Mocks fetching order history."""
        logging.info(f"Mock order_history for: {order_id}")
        time.sleep(0.2)  # Simulate network delay
        # Simulate a successful order
        return {
            'data': {
                'data': [
                    {
                        'ordSt': 'cmp',  # Mocked success status
                        'prc': 120.50,
                        'avgPrc': 120.45
                    }
                ]
            }
        }

    def subscribe(self, instrument_tokens_all):
        """Mocks the blocking subscription call."""
        logging.info(f"Subscribing to {len(instrument_tokens_all)} instruments. This will block this thread.")
        try:
            # Simulate a long-running process that blocks the thread
            time.sleep(300) 
        except KeyboardInterrupt:
            logging.info("Subscription thread interrupted.")
        logging.info("Subscription thread finished.")

class MockMsf:
    """Mocks your msf (MyStrategicFunctions?) module."""
    def __init__(self, neo_obj):
        self.neo_obj = neo_obj

    def execute_order_kotak_using_websocket(self, **kwargs):
        return self.neo_obj.execute_order_kotak_using_websocket(**kwargs)

    def get_exchange_segment(self, expiry_name):
        return "12345", "nse_fo"

    def get_details_for_expiry(self, expiry_name):
        return {'difference_between_strikes': 100}

    def get_ltp_for_index_using_kotak(self, expiry_name):
        return 22530.0

    def strike_to_symbol_kotak(self, expiry_name, strike, type_):
        return f"{expiry_name.upper()}-{strike}-{type_[0]}"

class MockConfig:
    """Mocks your config module."""
    def __init__(self, neo_obj):
        self.NEO_OBJ = neo_obj
        self.expiry_name = 'nifty'
        self.success_status_kotak = 'cmp'
        self.testing_mode = False
        
        # Mock TOKEN_MAP
        data = {
            'pTrdSymbol': [f'NIFTY-{s}-C' for s in range(20000, 25000, 100)] +
                          [f'NIFTY-{s}-P' for s in range(20000, 25000, 100)],
            'pSymbol': [str(random.randint(100000, 999999)) for _ in range(100)]
        }
        self.TOKEN_MAP = pd.DataFrame(data)
        
        # These will be populated by the subscribe function
        self.call_symbol_to_strike_map = {}
        self.put_symbol_to_strike_map = {}
        self.map_instrumenttoken_symbol_name = {}

def send_logs(message):
    """Mocks your logging function."""
    logging.error(message)

# --- Instantiate Mocks ---
# We create the mock objects that will be used by the functions
mock_neo = MockNeoObj()
config = MockConfig(mock_neo)
msf = MockMsf(mock_neo)


# --- Your Original Functions (Adapted for Mocks) ---
# These are your functions, unchanged except for using the mock objects.

def execute_order_for_symbol(symbol, quantity, type_of_order, producttype, validity, expiry_name, filename):
    """
    Executes an order and logs it to a file.
    This function is I/O bound (network calls, file write) and is a
    perfect candidate to be run in a separate thread.
    """
    logging.info(f"Executing order for {symbol}...")
    # Use 'a' mode to append to the file. 
    # Use a 'with' statement for safer file handling.
    try:
        with open(filename, "a") as f:
            symbolorder = msf.execute_order_kotak_using_websocket(
                symbol=symbol, type_=type_of_order, quant=quantity, price=None,
                trig_price=None, product=producttype, validity=validity, 
                expiry_name=expiry_name
            )
            
            fetched_order = None
            # Retry logic
            for _ in range(3): # Simple 3-retry loop
                try:
                    fetched_order_data = config.NEO_OBJ.order_history(order_id=symbolorder)
                    fetched_order = fetched_order_data['data']['data']
                    if fetched_order:
                        break # Success, exit loop
                except Exception as e:
                    logging.warning(f"Failed to fetch order history for {symbolorder}: {e}. Retrying...")
                    time.sleep(0.2)
            
            if not fetched_order:
                send_logs(f"Failed to fetch order history for {symbolorder} after retries.")
                return False

            if fetched_order[0]['ordSt'] == config.success_status_kotak:
                executed_price = fetched_order[0]['prc'] if config.testing_mode else fetched_order[0]['avgPrc']
                f.write(f"{symbolorder}\t{type_of_order}\t{symbol}\t{quantity}\t{executed_price}\n")
                logging.info(f"Successfully executed and logged order {symbolorder} for {symbol}.")
            else:
                # Optional: Add another sleep/retry if status wasn't final
                logging.warning(f"Order {symbolorder} status not successful: {fetched_order[0]['ordSt']}")
                send_logs(f"Something Wrong with Order {symbolorder} CHeck Now")
                return False
        
        return True
        
    except Exception as e:
        send_logs(f"Error in execute_order_for_symbol for {symbol}: {e}")
        return False


def subscribe_to_option_datafeed_optionchain(depth=25):
    """
    Calculates option chain and subscribes to data feed.
    The subscription itself is correctly started in a new thread.
    """
    logging.info("Calculating strikes and subscribing to feed...")
    
    expiry_name = config.expiry_name
    map_instrumenttoken_symbol_name = {}
    a, b = msf.get_exchange_segment(expiry_name)
    map_instrumenttoken_symbol_name[str(a)] = config.expiry_name
    
    client = config.NEO_OBJ
    details = msf.get_details_for_expiry(expiry_name)
    diff_between_two_strikes = details['difference_between_strikes']

    symbol_cur_price = float(msf.get_ltp_for_index_using_kotak(expiry_name))

    # Calculate nearer strike
    nearer_strike = round(symbol_cur_price / diff_between_two_strikes) * diff_between_two_strikes

    # Get strikes for watchlist
    strikes = [
        strike for strike in range(
            nearer_strike - depth * diff_between_two_strikes, 
            nearer_strike + (depth + 1) * diff_between_two_strikes, 
            diff_between_two_strikes
        )
    ]
    
    call_instrument_tokens = []
    put_instrument_tokens = []
    call_symbol_to_strike_map = {}
    put_symbol_to_strike_map = {}

    for strike in strikes:
        call_symbol_kotak = msf.strike_to_symbol_kotak(expiry_name, strike, "CALL")
        put_symbol_kotak = msf.strike_to_symbol_kotak(expiry_name, strike, "PUT")
        
        call_symbol_to_strike_map[call_symbol_kotak] = strike
        put_symbol_to_strike_map[put_symbol_kotak] = strike
        
        # Common logic for getting token
        def get_token_details(symbol, instrument_list):
            symbol_data = config.TOKEN_MAP.loc[config.TOKEN_MAP['pTrdSymbol'] == symbol]
            if len(symbol_data) == 0:
                send_logs(f'Invalid symbol {symbol}')
                return
            
            symbol_token = symbol_data.iloc[0]['pSymbol']
            exchange_segment = "bse_fo" if expiry_name in ['sensex', 'bankex'] else "nse_fo"
            
            instrument_list.append({"instrument_token": str(symbol_token), "exchange_segment": exchange_segment})
            map_instrumenttoken_symbol_name[str(symbol_token)] = symbol

        get_token_details(call_symbol_kotak, call_instrument_tokens)
        get_token_details(put_symbol_kotak, put_instrument_tokens)
    
    # for option_chain_data
    config.call_symbol_to_strike_map = call_symbol_to_strike_map
    config.put_symbol_to_strike_map = put_symbol_to_strike_map
    config.map_instrumenttoken_symbol_name = map_instrumenttoken_symbol_name
    
    instrument_tokens_all = [{"instrument_token": str(a), "exchange_segment": str(b)}] + call_instrument_tokens + put_instrument_tokens
    
    logging.info(f"Starting subscription thread for {len(instrument_tokens_all)} instruments...")
    # This is your original, correct threading for the subscription
    threading.Thread(
        target=client.subscribe, 
        args=(instrument_tokens_all,),
        name="SubscriptionThread", # Give the thread a name for easier debugging
        daemon=True # Mark as daemon so it exits when main thread exits
    ).start()


# --- Main Execution ---
# This demonstrates how to use the ThreadPoolExecutor

if __name__ == "__main__":
    
    # Create a ThreadPoolExecutor to manage order execution threads
    # We set max_workers=10, meaning up to 10 orders can run at the same time.
    
    # We use a 'with' statement, which automatically manages the pool's lifecycle
    # (starts the pool and shuts it down cleanly when done)
    with ThreadPoolExecutor(max_workers=10, thread_name_prefix="OrderExecutor") as executor:
        
        logging.info("MainThread: Starting subscription...")
        # This function will start its own background thread for the websocket
        subscribe_to_option_datafeed_optionchain(depth=5)
        
        logging.info("MainThread: Subscription started in background.")
        time.sleep(1) # Give subscription time to start (in real app, might not be needed)

        # --- Submit Orders to the Thread Pool ---
        # These calls are NON-BLOCKING. The 'executor.submit' returns
        # immediately, and the function runs on a worker thread.
        
        logging.info("MainThread: Submitting orders to thread pool...")
        
        # Submit a BUY order
        executor.submit(
            execute_order_for_symbol,
            symbol="NIFTY-22500-C",
            quantity=50,
            type_of_order="BUY",
            producttype="MIS",
            validity="DAY",
            expiry_name="nifty",
            filename="orders.log"
        )
        
        # Submit a SELL order
        executor.submit(
            execute_order_for_symbol,
            symbol="NIFTY-22600-P",
            quantity=50,
            type_of_order="SELL",
            producttype="MIS",
            validity="DAY",
            expiry_name="nifty",
            filename="orders.log"
        )
        
        # Submit another BUY order
        executor.submit(
            execute_order_for_symbol,
            symbol="NIFTY-22700-C",
            quantity=100,
            type_of_order="BUY",
            producttype="MIS",
            validity="DAY",
            expiry_name="nifty",
            filename="orders.log"
        )
        
        logging.info("MainThread: All orders submitted.")
        
        # The main thread is now free to do other work while
        # orders are executing in the background.
        for i in range(5):
            logging.info(f"MainThread: Doing other work... ({i+1}/5)")
            time.sleep(0.5)
            
    # The 'with' block has ended, which tells the executor to
    # wait for all submitted tasks to complete before exiting.
    logging.info("MainThread: All order tasks complete. Exiting.")
    # Note: The daemon subscription thread will be terminated automatically.
