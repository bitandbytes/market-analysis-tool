import pandas as pd
from typing import Dict, Any
from core.interfaces import AnalysisPluginInterface

class PriceHistoryPlugin(AnalysisPluginInterface):
    def get_name(self) -> str:
        return "Price History"

    def get_description(self) -> str:
        return "Plots the daily historical price (Adjusted Close).\nUseful for visualizing the stock's\nabsolute price trend over the selected period."

    def analyze(self, ticker_str: str, financials: pd.DataFrame, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Returns the daily Closing/Adj Closing price.
        """
        results = {}
        
        if market_data.empty:
            return {"error": "Insufficient market data"}
        
        # Prefer Adj Close, fallback to Close
        if 'Adj Close' in market_data.columns:
            price_series = market_data['Adj Close']
            results['summary'] = f"Plotting Adjusted Close Price for {ticker_str}."
        elif 'Close' in market_data.columns:
            price_series = market_data['Close']
            results['summary'] = f"Plotting Close Price for {ticker_str}."
        else:
            return {"error": "Price data not found in market data"}
            
        # Ensure it's a Series with date index
        results['chart_data'] = price_series
        
        return results
