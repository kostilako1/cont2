from flask import Flask, render_template, request, make_response
from ib_insync import *
import config
import pandas as pd
import nest_asyncio

nest_asyncio.apply()

app = Flask(__name__)

# Global cache for account and position data
cached_data = {
    'account_summary': {},
    'display_positions': []
}

def get_ib_connection():
    ib = IB()
    try:
        ib.connect(config.IBKR_HOST, config.IBKR_PORT, clientId=config.CLIENT_ID + 1)
        return ib
    except Exception:
        return None

@app.route('/')
def dashboard():
    global cached_data

    if not cached_data['account_summary'] or not cached_data['display_positions']:
        ib = get_ib_connection()
        if not ib: return "Error: Could not connect to IBKR TWS/Gateway."

        try:
            # --- Fetch Account and Position Data ---
            account_summary = {item.tag: item.value for item in ib.accountSummary() if item.tag in ['EquityWithLoanValue', 'BuyingPower']}
            positions = ib.positions()
            print(f"DEBUG: Positions fetched: {positions}") # Debug print
            
            # --- Get Tickers for Live Market Data and build a new list ---
            display_positions = []
            if positions:
                contracts = [p.contract for p in positions]
                tickers = ib.reqTickers(*contracts)
                ib.sleep(1) # Give tickers time to update

                for i, p in enumerate(positions):
                    ticker = tickers[i]
                    market_price = ticker.last if not pd.isna(ticker.last) else p.avgCost
                    market_value = p.position * market_price
                    pnl_data = ib.reqPnLSingle(p.account, '', p.contract.conId)
                    ib.sleep(0.5) # Give it a bit more time for PnL data to update
                    print(f"DEBUG: Raw PnL data for {p.contract.symbol}: {pnl_data}") # Debug print for raw PnL data
                    daily_pnl = 0
                    if pnl_data and not pd.isna(pnl_data.dailyPnL):
                        daily_pnl = pnl_data.dailyPnL
                    print(f"DEBUG: Daily PnL for {p.contract.symbol}: {daily_pnl}") # Debug print for PnL

                    display_positions.append({
                        'symbol': p.contract.symbol,
                        'qty': p.position,
                        'avgCost': p.avgCost,
                        'marketValue': market_value,
                        'dailyPnl': daily_pnl
                    })
            
            cached_data['account_summary'] = account_summary
            cached_data['display_positions'] = display_positions

        finally:
            ib.disconnect()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    start = (page - 1) * per_page
    end = start + per_page
    paginated_positions = cached_data['display_positions'][start:end]

    total_daily_pnl = sum(pos['dailyPnl'] for pos in cached_data['display_positions'])

    return render_template('index.html', 
        account=cached_data['account_summary'], 
        positions=paginated_positions, 
        page=page, 
        total_pages=(len(cached_data['display_positions']) // per_page) + 1,
        total_daily_pnl=total_daily_pnl
    )

@app.route('/download_data')
def download_data():
    global cached_data

    # Ensure data is populated
    if not cached_data['account_summary'] or not cached_data['display_positions']:
        # This will trigger a data fetch if not already done
        dashboard()

    csv_output = ""

    # Account Summary
    csv_output += "Account Summary\n"
    for key, value in cached_data['account_summary'].items():
        csv_output += f"{key},{value}\n"
    csv_output += "\n"

    # Positions Data
    csv_output += "Positions\n"
    if cached_data['display_positions']:
        # CSV Header
        csv_output += ",".join(cached_data['display_positions'][0].keys()) + "\n"
        # CSV Rows
        for pos in cached_data['display_positions']:
            csv_output += ",".join(str(pos[key]) for key in pos.keys()) + "\n"
    else:
        csv_output += "No open positions.\n"

    response = make_response(csv_output)
    response.headers["Content-Disposition"] = "attachment; filename=dashboard_data.csv"
    response.headers["Content-type"] = "text/csv"
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')