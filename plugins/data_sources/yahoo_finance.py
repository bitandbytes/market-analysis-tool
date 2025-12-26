import yfinance as yf
import pandas as pd
from core.interfaces import DataSourceInterface
from typing import Tuple

class YahooFinancePlugin(DataSourceInterface):
    def get_name(self) -> str:
        return "Yahoo Finance"

    def fetch_data(self, ticker: str, period: str = "5y") -> Tuple[pd.DataFrame, pd.DataFrame]:
        market_data = self._fetch_market_data(ticker, period=period)
        financials = self._fetch_financials(ticker, market_data)
        
        return market_data, financials

    def _fetch_financials(self, ticker: str, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Fetches financial statements from Yahoo Finance.
        Merges Balance Sheet, Income Statement, and Cash Flow.
        """
        financials = pd.DataFrame(index=market_data.index)
        
        try:
            # Fetch daily eps
            eps_data = self._fetch_daily_eps(ticker, market_data)
            if not eps_data.empty:
                financials['TTM EPS'] = eps_data

            return financials
        except Exception as e:
            print(f"Error fetching financials for {ticker}: {e}")
            return pd.DataFrame()

    def _fetch_daily_eps(self, ticker: str, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Fetches quartely eps data and interpolates it to daily data
        """
        try:
            ticker = yf.Ticker(ticker)
            quarterly_eps = ticker.earnings_dates[['Reported EPS']].dropna()
            
            # Normalize EPS dates to midnight and remove timezone for alignment
            quarterly_eps.index = quarterly_eps.index.tz_localize(None).normalize()
            
            # Sort to ensure rolling calculation works correctly
            quarterly_eps.sort_index(inplace=True)
            
            # Calculate Trailing Twelve Months (TTM) EPS
            # Rolling sum of the last 4 quarters
            ttm_eps = quarterly_eps.rolling(window=4, min_periods=4).sum()
            
            # Prepare market data index for alignment (naive and normalized)
            market_index_naive = market_data.index.tz_localize(None).normalize()

            # Reindex TTM EPS to the combined index of market dates and report dates
            # This ensures we have the TTM value on the day it was reported
            combined_index = market_index_naive.union(ttm_eps.index).sort_values()
            aligned_ttm = ttm_eps.reindex(combined_index)
            
            # Forward fill the TTM EPS values
            # The TTM EPS remains constant until the next earnings report
            daily_ttm = aligned_ttm.ffill()
            
            # Filter back to only the market data dates
            final_eps = daily_ttm.reindex(market_index_naive)
            
            # Restore the original market data index (with timezone if it had one)
            final_eps.index = market_data.index
            
            return final_eps
        except Exception as e:
            print(f"Error fetching TTM EPS for {ticker}: {e}")
            return pd.DataFrame()

    def _fetch_market_data(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        try:
            ticker_obj = yf.Ticker(ticker)
            history = ticker_obj.history(period=period, auto_adjust=False)

            price_data = history[['Adj Close']]

            return price_data.sort_index()
        except Exception as e:
            print(f"Error fetching market data for {ticker}: {e}")
            return pd.DataFrame()
