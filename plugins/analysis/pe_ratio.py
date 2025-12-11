import pandas as pd
from typing import Dict, Any
from core.interfaces import AnalysisPluginInterface

class PERatioPlugin(AnalysisPluginInterface):
    def get_name(self) -> str:
        return "P/E Ratio Analysis"

    def analyze(self, ticker: str, financials: pd.DataFrame, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates P/E Ratio.
        P/E = Market Price / TTM EPS
        """
        results = {}
        
        if financials.empty or market_data.empty:
            return {"error": "Insufficient data"}
        
        # Check for TTM EPS
        if 'TTM EPS' not in financials.columns:
             return {"error": "TTM EPS data not found in financials"}
        
        # Check for Price (prefer Adj Close, fallback to Close)
        if 'Adj Close' in market_data.columns:
            price_col = 'Adj Close'
        elif 'Close' in market_data.columns:
            price_col = 'Close'
        else:
            return {"error": "Price data (Adj Close/Close) not found in market data"}
            
        # Data is already aligned from the data source
        combined = pd.DataFrame(index=market_data.index)
        combined['Price'] = market_data[price_col]
        combined['TTM EPS'] = financials['TTM EPS']
        
        # Calculate P/E
        combined['PE_Ratio'] = combined['Price'] / combined['TTM EPS']
        
        # Drop NaNs
        combined.dropna(subset=['PE_Ratio'], inplace=True)
        
        # results['metrics'] = combined[['PE_Ratio']]
        results['chart_data'] = combined['PE_Ratio']
        results['summary'] = f"Calculated P/E Ratio for {ticker} using TTM EPS."
        
        return results
