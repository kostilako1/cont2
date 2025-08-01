import pandas as pd

def get_tickers():
    """Fetches the list of S&P 500 tickers from Wikipedia."""
    try:
        # Wikipedia page with the list of S&P 500 companies
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        # Read the HTML table into a pandas DataFrame
        tables = pd.read_html(url)
        sp500_table = tables[0]
        # Get the 'Symbol' column as a list
        tickers = sp500_table['Symbol'].tolist()
        # Clean up tickers for IBKR
        tickers = [t.replace('-', '.') for t in tickers] # For BRK-B -> BRK.B
        # Add more specific cleanups if needed
        return tickers
    except Exception as e:
        print(f"Could not fetch S&P 500 tickers: {e}")
        return []

def save_tickers(tickers):
    """Saves the list of tickers to a file."""
    with open('sp500_symbols.txt', 'w') as f:
        for ticker in tickers:
            f.write(f"{ticker}\n")
    print(f"Successfully saved {len(tickers)} S&P 500 tickers to sp500_symbols.txt")

if __name__ == "__main__":
    sp500_tickers = get_tickers()
    if sp500_tickers:
        save_tickers(sp500_tickers)
