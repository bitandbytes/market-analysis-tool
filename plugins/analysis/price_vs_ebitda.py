from typing import Dict, Any
import pandas as pd
from core.interfaces import AnalysisPluginInterface

class PriceVsEBITDAPlugin(AnalysisPluginInterface):
    def get_name(self) -> str:
        return "Price vs EBITDA"

    def get_description(self) -> str:
        return "Compares Stock Price vs EBITDA (TTM).\n"\
               "Plots the cumulative percentage change from the\n"\
               "start of the period to visualize relative growth\n"\
               "and potential divergence."

    def analyze(self, ticker_str: str, financials: pd.DataFrame, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Plots Price and EBITDA (TTM) indexed to 100.
        """
        results = {}
        if financials.empty or market_data.empty:
            return {"error": "Insufficient data"}

        # 1. Get EBITDA
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
        combined['EBITDA'] = ebitda.reindex(market_data.index, method='ffill')
        
        # Drop rows where we don't have both (usually just the start if EBITDA history is shorter)
        combined.dropna(inplace=True)

        if combined.empty:
             return {"error": "No overlapping data for Price and EBITDA"}

        # 4. Normalize to 100
        # Divide by the first value and multiply by 100
        first_price = combined['Price'].iloc[0]
        first_ebitda = combined['EBITDA'].iloc[0]
        
        if first_price == 0 or first_ebitda == 0:
             return {"error": "Initial Price or EBITDA is 0, cannot calculate percentage change."}

        # Calculate Cumulative % Change: ((Current / Start) - 1) * 100
        combined['Price (% Change)'] = ((combined['Price'] / first_price) - 1) * 100
        combined['EBITDA (% Change)'] = ((combined['EBITDA'] / first_ebitda) - 1) * 100

        results['chart_data'] = combined[['Price (% Change)', 'EBITDA (% Change)']]
        results['summary'] = f"Comparing Price vs EBITDA for {ticker_str} (% Change)."

        return results
