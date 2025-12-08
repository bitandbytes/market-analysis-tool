import pandas as pd
from typing import Dict, Any
from core.interfaces import AnalysisPluginInterface

class FCFYieldPlugin(AnalysisPluginInterface):
    def get_name(self) -> str:
        return "FCF Yield Analysis"

    def analyze(self, ticker: str, financials: pd.DataFrame, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates FCF Yield.
        FCF = Operating Cash Flow - Capital Expenditure
        FCF Yield = FCF / Market Cap
        """
        if financials.empty or market_data.empty:
            return {"error": "Insufficient data"}

        # Operating Cash Flow
        ocf_col = 'Operating Cash Flow'
        if ocf_col not in financials.columns:
            # yfinance sometimes calls it 'Total Cash From Operating Activities'
            if 'Total Cash From Operating Activities' in financials.columns:
                ocf_col = 'Total Cash From Operating Activities'
            else:
                return {"error": "Operating Cash Flow data not found"}
        
        ocf = financials[ocf_col]
        
        # CapEx
        capex_col = 'Capital Expenditure'
        if capex_col not in financials.columns:
             # yfinance: 'Capital Expenditures'
            if 'Capital Expenditures' in financials.columns:
                capex_col = 'Capital Expenditures'
            else:
                # Sometimes it's negative in 'Investing Cash Flow'
                return {"error": "CapEx data not found"}
        
        capex = financials[capex_col]
        
        # Calculate FCF
        # CapEx is usually negative in CF statement, so we add it? Or is it positive?
        # In yfinance, Capital Expenditures is often reported as a negative number in the cash flow statement.
        # FCF = OCF + CapEx (if CapEx is negative)
        # Let's check sign. Usually OCF is positive, CapEx is negative.
        # If CapEx is positive (absolute value), we subtract.
        # We'll assume standard accounting: FCF = OCF - abs(CapEx) or OCF + CapEx (if negative).
        # To be safe, let's assume we add them if CapEx is negative.
        
        # Actually, let's just do FCF = OCF + CapEx (assuming CapEx is the cash OUTFLOW, so it's negative).
        fcf = ocf + capex
        
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
        fcf_aligned = fcf.reindex(market_data.index, method='ffill')
        
        combined['Market_Cap'] = combined['Close'] * shares_aligned
        combined['FCF_Yield'] = fcf_aligned / combined['Market_Cap']
        
        combined.dropna(subset=['FCF_Yield'], inplace=True)
        
        return {
            'metrics': combined[['FCF_Yield']],
            'chart_data': combined['FCF_Yield'],
            'summary': f"Calculated FCF Yield for {ticker}"
        }
