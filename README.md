# Interactive Brokers (IBKR) Trading Bot

This bot uses a contrarian strategy to trade the S&P 500 (SPY) via the Interactive Brokers API.

## CRITICAL: How it Works

This bot connects to the **Trader Workstation (TWS)** or **IBKR Gateway** software running on your desktop. It does NOT connect to IBKR's servers directly.

**You MUST have TWS or the Gateway running and logged in for the bot to work.**

## Setup Instructions

### 1. Install and Configure TWS/Gateway

1.  Download and install the latest version of [Trader Workstation (TWS)](https://www.interactivebrokers.com/en/trading/tws.php).
2.  Log in to TWS using your **Paper Trading Account** credentials.
3.  **Enable API Access:**
    *   In TWS, go to **File > Global Configuration**.
    *   Select **API > Settings** from the left panel.
    *   Check the box for **"Enable ActiveX and Socket Clients"**.
    *   Make sure the **Socket port** number matches the `IBKR_PORT` in your `config.py` file (default is `7497` for paper trading).
    *   It is recommended to add `127.0.0.1` to the **"Trusted IP Addresses"**.

### 2. Install Python Dependencies

```bash
# Make sure you are in the project directory (C:\Users\User\Downloads\cont2)
py -m pip install -r requirements.txt
```

### 3. Configure the Bot

Open `config.py` and review the settings. The default `IBKR_HOST` and `IBKR_PORT` should work for a standard TWS setup.

## Usage

### 1. Run the Trading Bot

Make sure TWS is running and you are logged in. Then, run the main script:

```bash
py main.py
```

The bot will connect to TWS, check for trading signals, and then disconnect.

### 2. Run the Visual Dashboard

To view the dashboard, run the following command in a separate terminal:

```bash
py dashboard.py
```

Then, open your web browser and navigate to `http://127.0.0.1:5000`.