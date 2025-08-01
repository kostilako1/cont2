from ib_insync import *
import pandas as pd
import config
import nest_asyncio

nest_asyncio.apply()

def run_backtest(symbol, start_date, end_date, capital, risk_percent, buy_threshold, stop_loss_percent, take_profit_percent, holding_period_days):
    ib = IB()
    try:
        ib.connect(config.IBKR_HOST, config.IBKR_PORT, clientId=config.CLIENT_ID + 2)
    except Exception as e:
        print(f"Could not connect to IBKR for historical data: {e}")
        return

    contract = Stock(symbol, 'SMART', 'USD')
    ib.qualifyContracts(contract)

    # --- 1. Download Historical Data ---
    # IBKR data requests are more complex, this is a simplified example
    # It's often better to use a dedicated historical data provider for extensive backtests
    duration = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
    bars = ib.reqHistoricalData(
        contract,
        endDateTime=pd.to_datetime(end_date).strftime("%Y%m%d %H:%M:%S"),
        durationStr=f'{duration} D',
        barSizeSetting='1 day',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1
    )
    ib.disconnect()

    if not bars:
        print("No historical data found for the given symbol and date range.")
        return
    
    data = util.df(bars)

    # --- (The rest of the backtesting logic remains largely the same) ---
    # ... (simulation loop, performance calculation, etc.)
    print("--- Backtest Results (IBKR Data) ---")
    # ... (print results)

if __name__ == '__main__':
    run_backtest(
        symbol=config.SYMBOL,
        start_date="2022-01-01", # Shorter period for IBKR data request
        end_date="2023-12-31",
        capital=config.TRADING_CAPITAL,
        risk_percent=config.RISK_PERCENT,
        buy_threshold=2.0,
        stop_loss_percent=config.STOP_LOSS_PERCENT,
        take_profit_percent=config.TAKE_PROFIT_PERCENT,
        holding_period_days=config.HOLDING_PERIOD_DAYS
    )