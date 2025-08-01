from ib_insync import *
import pandas as pd
import config
import logging
import os
import nest_asyncio
import time
import json
from datetime import datetime, date
import yfinance as yf

nest_asyncio.apply()

# --- State Management ---
STATE_FILE = os.path.join(os.path.dirname(__file__), 'run_state.json')

def read_run_state():
    """Reads the last run date and next start index from the state file."""
    if not os.path.exists(STATE_FILE):
        return {'last_run_date': None, 'next_start_index': 0}
    with open(STATE_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {'last_run_date': None, 'next_start_index': 0}

def write_run_state(state):
    """Writes the current state to the state file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

class IBKR_Final_Bot:
    def __init__(self):
        self.ib = IB()
        self.all_symbols = self.load_all_symbols()
        self.trades = self.load_trades() # Load existing trade records

    def load_trades(self, filename="trades.csv"):
        """Loads trade records from a CSV file."""
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename)
                # Convert 'purchase_timestamp' back to datetime objects
                if 'purchase_timestamp' in df.columns:
                    df['purchase_timestamp'] = pd.to_datetime(df['purchase_timestamp'])
                logging.info(f"Loaded {len(df)} trade records from {filename}")
                return df.to_dict(orient='records')
            except Exception as e:
                logging.error(f"Error loading trades from {filename}: {e}")
                return []
        return []

    def load_all_symbols(self):
        try:
            with open('sp500_symbols.txt', 'r') as f:
                return [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            logging.error("sp500_symbols.txt not found.")
            return []

    def connect(self):
        try:
            self.ib.connect(config.IBKR_HOST, config.IBKR_PORT, clientId=config.CLIENT_ID)
            return True
        except Exception as e:
            logging.error(f"Failed to connect to IBKR: {e}")
            return False

    def is_market_open(self):
        """Checks if the US stock market is currently open."""
        try:
            contract = Stock('SPY', 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            cd = self.ib.reqContractDetails(contract)[0]
            tz = pytz.timezone(cd.timeZoneId)
            now = datetime.now(tz)
            
            # This is a simplified check. A robust version would parse the liquidHours string.
            # For now, we'll check for standard US market hours.
            if now.weekday() >= 5: return False # It's Saturday or Sunday
            if now.hour < 9 or (now.hour == 9 and now.minute < 30) or now.hour >= 16:
                return False # It's outside 9:30 AM - 4:00 PM
            return True
        except Exception as e:
            logging.error(f"Could not determine market hours: {e}")
            return False # Fail safe

    def get_price_and_daily_change_from_yfinance(self, symbol):
        """Fetches current price and daily percentage change for a symbol."""
        try:
            history = yf.Ticker(symbol).history(period='2d') # Get last 2 days for daily change
            if not history.empty and len(history) >= 2:
                current_price = history['Close'].iloc[-1]
                previous_close = history['Close'].iloc[-2]
                if previous_close != 0:
                    daily_change = ((current_price - previous_close) / previous_close) * 100
                    return current_price, daily_change
            return None, None
        except Exception as e:
            logging.error(f"Error fetching price and daily change for {symbol}: {e}")
            return None, None

    def place_order(self, contract, qty):
        order = MarketOrder('BUY', qty)
        trade = self.ib.placeOrder(contract, order)
        purchase_time = datetime.now()
        self.trades.append({
            'time': purchase_time.strftime("%Y-%m-%d %H:%M:%S"),
            'symbol': contract.symbol,
            'action': 'BUY',
            'quantity': qty,
            'price': trade.orderStatus.avgFillPrice if trade.orderStatus.avgFillPrice else 'N/A',
            'purchase_timestamp': purchase_time # Store datetime object for calculation
        })
        logging.info(f"Placed BUY order for {qty} of {contract.symbol}.")

    def save_trades_to_csv(self, filename="trades.csv"):
        if self.trades:
            # Create a copy to avoid modifying the original list during iteration
            trades_for_csv = []
            for trade in self.trades:
                trade_copy = trade.copy()
                # Convert datetime object to string for CSV export if it exists
                if 'purchase_timestamp' in trade_copy and isinstance(trade_copy['purchase_timestamp'], datetime):
                    trade_copy['purchase_timestamp'] = trade_copy['purchase_timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                trades_for_csv.append(trade_copy)

            df = pd.DataFrame(trades_for_csv)
            df.to_csv(filename, index=False)
            logging.info(f"Trades saved to {filename}")
        else:
            logging.info("No trades to save.")

    def manage_positions_with_holding_period(self):
        """Checks current positions and enforces a 48-hour holding period."""
        logging.info("Checking current positions for holding period enforcement...")
        positions = self.ib.positions()
        if not positions:
            logging.info("No open positions to manage.")
            return

        for p in positions:
            symbol = p.contract.symbol
            # Find the purchase record for this symbol
            # This assumes one position per symbol, or takes the latest purchase
            purchase_record = next((t for t in reversed(self.trades) if t['symbol'] == symbol and t['action'] == 'BUY'), None)

            if purchase_record and 'purchase_timestamp' in purchase_record:
                purchase_time = purchase_record['purchase_timestamp']
                time_held = datetime.now() - purchase_time
                
                if time_held.total_seconds() >= 48 * 3600: # 48 hours in seconds
                    logging.info(f"Position in {symbol} has been held for {time_held}. Eligible for sale.")
                    # TODO: Add actual selling logic here based on a sell signal
                else:
                    remaining_time = (48 * 3600) - time_held.total_seconds()
                    hours_remaining = remaining_time / 3600
                    logging.info(f"Position in {symbol} held for {time_held}. {hours_remaining:.2f} hours remaining in holding period.")
            else:
                logging.warning(f"Could not find purchase record for {symbol}. Cannot enforce holding period.")

    def run(self):
        if not self.connect(): return

        # 1. Check Market Hours
        # if not self.is_market_open():
        #     logging.info("Market is closed. The bot will not run.")
        #     self.ib.disconnect()
        #     return

        # 2. Check Run State
        today_str = str(date.today())
        state = read_run_state()
        if state.get('last_run_date') == today_str:
            logging.info(f"Full scan for {today_str} has already been completed. The bot will not run again today.")
            self.ib.disconnect()
            return
        
        start_index = state.get('next_start_index', 0)
        if state.get('last_run_date') != today_str:
            logging.info(f"New day detected. Starting a fresh scan for {today_str}.")
            start_index = 0

        # 3. Main Execution Loop: Iterate through symbols and buy if red
        for symbol_str in self.all_symbols[start_index:]:
            logging.info(f"--- Processing {symbol_str} ---")
            contract = Stock(symbol_str, 'SMART', 'USD')
            try:
                self.ib.qualifyContracts(contract)
            except Exception as e:
                logging.warning(f"Could not qualify contract for {symbol_str}: {e}. Skipping.")
                continue

            current_price, daily_change = self.get_price_and_daily_change_from_yfinance(symbol_str)

            if current_price is None or daily_change is None:
                logging.warning(f"Could not get valid price or daily change for {symbol_str}. Skipping.")
                continue

            # Check if already holding this position from a recent trade (within 48 hours)
            already_holding_recently = False
            for trade_record in reversed(self.trades): # Check most recent trades first
                if trade_record['symbol'] == symbol_str and trade_record['action'] == 'BUY':
                    time_since_purchase = datetime.now() - trade_record['purchase_timestamp']
                    if time_since_purchase.total_seconds() < 48 * 3600: # Less than 48 hours
                        logging.info(f"Already holding {symbol_str} from a recent trade ({time_since_purchase.total_seconds() / 3600:.2f} hours ago). Skipping new buy order.")
                        already_holding_recently = True
                        break
            
            if already_holding_recently:
                continue

            if daily_change < 0: # If the stock is red
                logging.info(f"{symbol_str} is red ({daily_change:.2f}%). Placing buy order.")
                # Determine quantity (e.g., fixed dollar amount or fixed shares)
                # For now, let's use a fixed quantity for demonstration
                qty = 1 # Example quantity
                self.place_order(contract, qty)
            else:
                logging.info(f"{symbol_str} is not red ({daily_change:.2f}%). Skipping buy order.")

            # Update state after processing each symbol
            start_index += 1
            write_run_state({'last_run_date': None, 'next_start_index': start_index})
            time.sleep(1) # Small delay between processing symbols

        # 4. Manage existing positions based on holding period
        self.manage_positions_with_holding_period()

        # 5. Finalize and Reset
        write_run_state({'last_run_date': today_str, 'next_start_index': 0})
        logging.info(f"Full scan for {today_str} complete. State has been reset for the next day.")
        self.save_trades_to_csv()
        self.ib.disconnect()

if __name__ == "__main__":
    import pytz
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    bot = IBKR_Final_Bot()
    bot.run()
