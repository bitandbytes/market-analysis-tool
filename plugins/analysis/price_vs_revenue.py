from typing import Dict, Any
import pandas as pd
from core.interfaces import AnalysisPluginInterface

class PriceVsRevenuePlugin(AnalysisPluginInterface):
    def get_name(self) -> str:
        return "Price vs Revenue"

    def get_description(self) -> str:
        return "Compares Stock Price vs Total Revenue (TTM).\n"\
               "Plots the cumulative percentage change from the\n"\
               "start of the period to visualize relative growth\n"\
               "and potential divergence."

    def analyze(self, ticker_str: str, financials: pd.DataFrame, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Plots Price and Revenue (TTM) indexed to 100.
        """
        results = {}
        if financials.empty or market_data.empty:
            return {"error": "Insufficient data"}

        # 1. Get Revenue
        rev_col = 'Total Revenue'
        if rev_col not in financials.columns:
             return {"error": "Revenue data not found"}
        
        revenue = financials[rev_col]

        # 2. Get Price
        if 'Adj Close' in market_data.columns:
            price_col = 'Adj Close'
        elif 'Close' in market_data.columns:
            price_col = 'Close'
        else:
            return {"error": "Price data not found"}

        # 3. Align Data
        combined = pd.DataFrame(index=market_data.index)
        combined['Price'] = market_data[price_col]
        combined['Revenue'] = revenue.reindex(market_data.index, method='ffill')
        
        # Drop rows where we don't have both
        combined.dropna(inplace=True)

        if combined.empty:
             return {"error": "No overlapping data for Price and Revenue"}

        # 4. Normalize to 100
        first_price = combined['Price'].iloc[0]
        first_rev = combined['Revenue'].iloc[0]
        
        if first_price == 0 or first_rev == 0:
             return {"error": "Initial Price or Revenue is 0, cannot calculate percentage change."}

        # Calculate Cumulative % Change: ((Current / Start) - 1) * 100
        combined['Price (% Change)'] = ((combined['Price'] / first_price) - 1) * 100
        combined['Revenue (% Change)'] = ((combined['Revenue'] / first_rev) - 1) * 100

        results['chart_data'] = combined[['Price (% Change)', 'Revenue (% Change)']]
        results['summary'] = f"Comparing Price vs Revenue for {ticker_str} (% Change)."

        return results
