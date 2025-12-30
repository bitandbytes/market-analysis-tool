from typing import Dict, Any
import pandas as pd
from core.interfaces import AnalysisPluginInterface

class PriceVsEPSPlugin(AnalysisPluginInterface):
    def get_name(self) -> str:
        return "Price vs EPS"

    def get_description(self) -> str:
        return "Compares Stock Price vs EPS (TTM).\n"\
               "Plots the cumulative percentage change from the\n"\
               "start of the period to visualize relative growth\n"\
               "and potential divergence."

    def get_category(self) -> str:
        return "Price vs Fundamentals"

    def analyze(self, ticker_str: str, financials: pd.DataFrame, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Plots Price and EPS (TTM) indexed to 100.
        """
        results = {}
        if financials.empty or market_data.empty:
            return {"error": "Insufficient data"}

        # 1. Get EPS
        eps_col = 'TTM EPS'
        if eps_col not in financials.columns:
             return {"error": "TTM EPS data not found"}
        
        eps = financials[eps_col]

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
        combined['EPS'] = eps.reindex(market_data.index, method='ffill')
        
        # Drop rows where we don't have both
        combined.dropna(inplace=True)

        if combined.empty:
             return {"error": "No overlapping data for Price and EPS"}

        # 4. Normalize to 100
        # Check if start values are positive. If negative, indexing is weird (e.g. -0.5 to 0.5 is huge growth).
        # But for visualization, let's just stick to the math: (Value / Base) * 100.
        # If base is negative, the index will flip signs. This is visually confusing but mathematically correct for growth.
        # A better approach for negative values might be: Value - Base (Relative Change) or just plot absolute values.
        # Given "Index to 100" is standard for stock charts, we'll try it.
        
        first_price = combined['Price'].iloc[0]
        first_eps = combined['EPS'].iloc[0]
        
        if first_price == 0:
             return {"error": "Initial Price is 0, cannot calculate percentage change."}
             
        if first_eps == 0:
            return {"error": "Initial EPS is 0, cannot calculate percentage change."}

        # Calculate Cumulative % Change: ((Current / Start) - 1) * 100
        combined['Price (% Change)'] = ((combined['Price'] / first_price) - 1) * 100
        combined['EPS (% Change)'] = ((combined['EPS'] / first_eps) - 1) * 100

        results['chart_data'] = combined[['Price (% Change)', 'EPS (% Change)']]
        results['summary'] = f"Comparing Price vs EPS for {ticker_str} (% Change)."

        return results
