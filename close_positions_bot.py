
from ib_insync import IB, MarketOrder

def close_all_positions():
    ib = IB()
    try:
        # Connect to IBKR TWS/Gateway
        # Assuming default host and port, adjust if necessary
        ib.connect('127.0.0.1', 7497, clientId=1) # Client ID 1 is commonly used for manual trading/bots
        print("Connected to IBKR TWS/Gateway.")

        # Get all open positions
        positions = ib.positions()
        if not positions:
            print("No open positions found.")
            return

        print(f"Found {len(positions)} open positions. Closing them now...")

        for pos in positions:
            contract = pos.contract
            position_size = pos.position # Positive for long, negative for short

            # Determine order action and quantity
            if position_size > 0:
                action = 'SELL'
                quantity = position_size
            else:
                action = 'BUY'
                quantity = -position_size # Make quantity positive for BUY order

            order = MarketOrder(action, quantity)
            trade = ib.placeOrder(contract, order)
            print(f"Placed {action} order for {quantity} shares of {contract.symbol} ({contract.secType}). Trade status: {trade.orderStatus.status}")

        ib.sleep(2) # Give some time for orders to be processed
        print("All position closing orders have been placed.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("Disconnected from IBKR.")

if __name__ == "__main__":
    close_all_positions()
