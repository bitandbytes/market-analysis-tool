import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from plugins.data_sources.yahoo_finance import YahooFinancePlugin
from plugins.analysis.price_vs_ebitda import PriceVsEBITDAPlugin
from plugins.analysis.price_vs_eps import PriceVsEPSPlugin
from plugins.analysis.price_vs_revenue import PriceVsRevenuePlugin

def verify_price_vs_metric():
    # Helper to mock data instead of calling API (faster/reliable)
    # But since we just fixed the API, let's use it for real integration test
    
    print("Fetching real data for AAPL...")
    source = YahooFinancePlugin()
    # Use 2 years to ensure enough history overlaps
    market_data, financials = source.fetch_data("AAPL", period="2y")
    
    if market_data.empty or financials.empty:
        print("[FAIL] Could not fetch data.")
        return

    plugins = [
        PriceVsEBITDAPlugin(),
        PriceVsEPSPlugin(),
        PriceVsRevenuePlugin()
    ]
    
    for plugin in plugins:
        print(f"\n--- Testing {plugin.get_name()} ---")
        try:
            results = plugin.analyze("AAPL", financials, market_data)
            
            if 'error' in results:
                # EPS might be error if negative start, but AAPL is profitable
                print(f"[WARN] Returned error: {results['error']}")
                continue
                
            chart_data = results.get('chart_data')
            
            if chart_data is None or chart_data.empty:
                print(f"[FAIL] Chart data is empty.")
                continue
                
            # Check structure
            if not isinstance(chart_data, pd.DataFrame):
                print(f"[FAIL] Chart data is not a DataFrame (Type: {type(chart_data)})")
                continue
                
            cols = chart_data.columns
            print(f"Columns: {list(cols)}")
            
            if len(cols) != 2:
                 print(f"[FAIL] Expected 2 columns, got {len(cols)}")
                 
            # Check Indexing to 100
            first_row = chart_data.iloc[0]
            print(f"First Row: {first_row.to_dict()}")
            
            # Allow small float error
            if np.isclose(first_row[0], 0.0) and np.isclose(first_row[1], 0.0):
                print(f"[PASS] Both series start at 0.0%")
            else:
                print(f"[FAIL] Series do not start at 0.0%")

        except Exception as e:
            print(f"[FAIL] Exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    verify_price_vs_metric()
