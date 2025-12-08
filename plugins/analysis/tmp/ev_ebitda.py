import pandas as pd
from typing import Dict, Any
from core.interfaces import AnalysisPluginInterface

class EVEBITDAPlugin(AnalysisPluginInterface):
    def get_name(self) -> str:
        return "EV/EBITDA Analysis"

    def analyze(self, ticker: str, financials: pd.DataFrame, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates EV/EBITDA.
        EV = Market Cap + Total Debt - Cash & Equivalents
        EBITDA = Operating Income + Depreciation & Amortization
        """
        if financials.empty or market_data.empty:
            return {"error": "Insufficient data"}

        # 1. Calculate EBITDA
        # yfinance often has 'EBITDA' directly, or we calculate it.
        # Let's try to find 'EBITDA' or calculate it.
        ebitda_col = 'EBITDA'
        if ebitda_col not in financials.columns:
            # Try Normalized EBITDA
            if 'Normalized EBITDA' in financials.columns:
                ebitda_col = 'Normalized EBITDA'
            else:
                # Try calculating: Operating Income + Reconciled Depreciation
                op_inc = financials.get('Operating Income', financials.get('EBIT', pd.Series()))
                dep = financials.get('Reconciled Depreciation', pd.Series())
                if not op_inc.empty:
                    financials['Calculated_EBITDA'] = op_inc.add(dep, fill_value=0)
                    ebitda_col = 'Calculated_EBITDA'
                else:
                    return {"error": "EBITDA data not found"}

        ebitda = financials[ebitda_col]

        # 2. Calculate EV components
        # Market Cap = Price * Shares Outstanding
        # We need Shares Outstanding. yfinance `history` doesn't give shares. 
        # `financials` might have 'Basic Average Shares' or 'Diluted Average Shares'.
        shares_col = 'Basic Average Shares'
        if shares_col not in financials.columns:
            if 'Diluted Average Shares' in financials.columns:
                shares_col = 'Diluted Average Shares'
            else:
                return {"error": "Shares data not found"}
        
        shares = financials[shares_col]
        
        # Total Debt
        debt_col = 'Total Debt'
        if debt_col not in financials.columns:
             # Try calculating: Long Term Debt + Current Debt
             # Simplified for now
             return {"error": "Total Debt data not found"}
        
        total_debt = financials[debt_col]
        
        # Cash
        cash_col = 'Cash And Cash Equivalents'
        if cash_col not in financials.columns:
             return {"error": "Cash data not found"}
        
        cash = financials[cash_col]

        # 3. Align and Calculate
        # We calculate EV/EBITDA based on the financial statement dates primarily, 
        # but we can also project it daily if we assume debt/cash/shares stay constant between reports 
        # and only Price changes.
        
        combined = pd.DataFrame(index=market_data.index)
        combined['Close'] = market_data['Close']
        
        # Forward fill financial metrics
        shares_aligned = shares.reindex(market_data.index, method='ffill')
        debt_aligned = total_debt.reindex(market_data.index, method='ffill')
        cash_aligned = cash.reindex(market_data.index, method='ffill')
        ebitda_aligned = ebitda.reindex(market_data.index, method='ffill')
        
        combined['Market_Cap'] = combined['Close'] * shares_aligned
        combined['EV'] = combined['Market_Cap'] + debt_aligned - cash_aligned
        combined['EV_EBITDA'] = combined['EV'] / ebitda_aligned
        
        combined.dropna(subset=['EV_EBITDA'], inplace=True)
        
        return {
            'metrics': combined[['EV_EBITDA']],
            'chart_data': combined['EV_EBITDA'],
            'summary': f"Calculated EV/EBITDA for {ticker}"
        }
