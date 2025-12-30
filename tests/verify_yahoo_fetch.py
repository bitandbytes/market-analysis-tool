
import sys
import os
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from plugins.data_sources.yahoo_finance import YahooFinancePlugin

def verify_yahoo_fetch():
    plugin = YahooFinancePlugin()
    ticker = "AAPL"
    
    print(f"Fetching data for {ticker}...")
    try:
        market_data, financials = plugin.fetch_data(ticker, period="1y")
        
        print("\n--- Market Data Head ---")
        print(market_data.head())
        
        print("\n--- Financials Head ---")
        print(financials.head())
        
        print("\n--- Financials Tail ---")
        print(financials.tail())
        
        expected_cols = ['TTM EPS', 'Basic Average Shares', 'Total Revenue', 'Operating Cash Flow', 'Capital Expenditure', 'EBITDA', 'Total Debt', 'Cash And Cash Equivalents']
        
        print("\n--- Column Verification ---")
        for col in expected_cols:
            if col in financials.columns:
                non_nan_count = financials[col].notna().sum()
                print(f"[PASS] {col} found. Non-NaN count: {non_nan_count}/{len(financials)}")
            else:
                print(f"[FAIL] {col} NOT found in financials columns.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_yahoo_fetch()
