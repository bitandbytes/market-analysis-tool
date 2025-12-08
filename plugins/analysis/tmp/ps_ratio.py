import pandas as pd
from typing import Dict, Any
from core.interfaces import AnalysisPluginInterface

class PSRatioPlugin(AnalysisPluginInterface):
    def get_name(self) -> str:
        return "P/S Ratio Analysis"

    def analyze(self, ticker: str, financials: pd.DataFrame, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates P/S Ratio.
        P/S = Market Cap / Total Revenue
        """
        if financials.empty or market_data.empty:
            return {"error": "Insufficient data"}

        # Revenue
        rev_col = 'Total Revenue'
        if rev_col not in financials.columns:
            return {"error": "Revenue data not found"}
        
        revenue = financials[rev_col]
        
        # Shares for Market Cap
        shares_col = 'Basic Average Shares'
        if shares_col not in financials.columns:
            if 'Diluted Average Shares' in financials.columns:
                shares_col = 'Diluted Average Shares'
            else:
                return {"error": "Shares data not found"}
        
        shares = financials[shares_col]
        
        # Align
        combined = pd.DataFrame(index=market_data.index)
        combined['Close'] = market_data['Close']
        
        shares_aligned = shares.reindex(market_data.index, method='ffill')
        revenue_aligned = revenue.reindex(market_data.index, method='ffill')
        
        # Note: Revenue in financials is usually Annual or TTM. 
        # If it's annual, P/S using annual revenue might be jumpy. 
        # Ideally we use TTM revenue. yfinance financials are usually annual if we just ask for `financials`.
        # For simplicity, we use the reported revenue (Annual) as the denominator for the period following the report.
        
        combined['Market_Cap'] = combined['Close'] * shares_aligned
        combined['PS_Ratio'] = combined['Market_Cap'] / revenue_aligned
        
        combined.dropna(subset=['PS_Ratio'], inplace=True)
        
        return {
            'metrics': combined[['PS_Ratio']],
            'chart_data': combined['PS_Ratio'],
            'summary': f"Calculated P/S Ratio for {ticker}"
        }
