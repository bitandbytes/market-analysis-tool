import yfinance as yf
import pandas as pd
from core.interfaces import DataSourceInterface
from typing import Tuple

class YahooFinancePlugin(DataSourceInterface):
    def get_name(self) -> str:
        return "Yahoo Finance"

    def fetch_data(self, ticker_str: str, period: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        market_data = self._fetch_market_data(ticker_str, period=period)
        financials = self._fetch_financials(ticker_str, market_data)
        
        return market_data, financials

    def _fetch_financials(self, ticker_str: str, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Fetches financial statements from Yahoo Finance.
        Merges Balance Sheet, Income Statement, and Cash Flow.
        """
        financials = pd.DataFrame(index=market_data.index)
        
        try:
            # Fetch daily eps
            eps_data = self._fetch_daily_eps(ticker_str, market_data)
            if not eps_data.empty:
                financials['TTM EPS'] = eps_data.iloc[:, 0]

            # Fetch shares
            shares_data = self._fetch_shares(ticker_str, market_data)
            if not shares_data.empty:
                financials['Basic Average Shares'] = shares_data.iloc[:, 0]

            # Fetch revenue
            revenue_data = self._fetch_revenue(ticker_str, market_data)
            if not revenue_data.empty:
                financials['Total Revenue'] = revenue_data.iloc[:, 0]
            
            return financials
        except Exception as e:
            print(f"Error fetching financials for {ticker_str}: {e}")
            return pd.DataFrame()

    def _fetch_daily_eps(self, ticker_str: str, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Fetches quartely eps data and interpolates it to daily data
        """
        try:
            ticker = yf.Ticker(ticker_str)
            
            # --- 1. Quarterly Data (Precise TTM from Earnings Dates) ---
            quarterly_eps = ticker.earnings_dates
            ttm_from_quarterly = pd.Series(dtype=float)
            
            if quarterly_eps is not None and not quarterly_eps.empty:
                if 'Reported EPS' in quarterly_eps.columns:
                    q_eps = quarterly_eps[['Reported EPS']].dropna()
                    q_eps.index = q_eps.index.tz_localize(None).normalize()
                    q_eps.sort_index(inplace=True)
                    # TTM: Sum last 4 quarters
                    ttm_from_quarterly = q_eps['Reported EPS'].rolling(window=4, min_periods=4).sum()

            # --- 2. Annual Data (Fallback) ---
            a_stmt = ticker.income_stmt
            annual_eps = pd.Series(dtype=float)
            
            if a_stmt is not None and not a_stmt.empty:
                a_stmt = a_stmt.T
                a_stmt.index = pd.to_datetime(a_stmt.index).tz_localize(None).normalize()
                a_stmt.sort_index(inplace=True)
                
                # Use Basic or Diluted EPS from Annual report? 
                # Usually P/E uses Diluted. Let's try Diluted, consistent with most sites.
                if 'Diluted EPS' in a_stmt.columns:
                    annual_eps = a_stmt['Diluted EPS']
                elif 'Basic EPS' in a_stmt.columns:
                     annual_eps = a_stmt['Basic EPS']

            # --- 3. Merge ---
            if ttm_from_quarterly.empty and annual_eps.empty:
                return pd.DataFrame()
                
            combined_index = ttm_from_quarterly.index.union(annual_eps.index).sort_values()
            combined_eps = pd.Series(index=combined_index, dtype=float)
            
            # Fill with Annual first
            combined_eps.update(annual_eps)
            # Overlay Quarterly TTM
            combined_eps.update(ttm_from_quarterly)
            
            # --- 4. Align ---
            market_index_naive = market_data.index.tz_localize(None).normalize()
            full_index = market_index_naive.union(combined_eps.index).sort_values()
            
            aligned_eps = combined_eps.reindex(full_index).ffill().bfill()
            final_eps = aligned_eps.reindex(market_index_naive)
            final_eps.index = market_data.index
            
            return final_eps.to_frame(name='TTM EPS') # Ensure consistent column name? 
            # Note: _fetch_financials uses .iloc[:, 0] so name doesn't matter too much, but good for debug
            
        except Exception as e:
            print(f"Error fetching TTM EPS for {ticker_str}: {e}")
            return pd.DataFrame()

    def _fetch_shares(self, ticker_str: str, market_data: pd.DataFrame) -> pd.DataFrame:
        try:
            ticker = yf.Ticker(ticker_str)
            
            # --- 1. Quarterly Data (Precise) ---
            q_stmt = ticker.quarterly_income_stmt
            shares_quarterly = pd.Series(dtype=float)

            if q_stmt is not None and not q_stmt.empty:
                q_stmt = q_stmt.T
                q_stmt.index = pd.to_datetime(q_stmt.index).tz_localize(None).normalize()
                q_stmt.sort_index(inplace=True)

                if 'Basic Average Shares' in q_stmt.columns:
                    shares_quarterly = q_stmt['Basic Average Shares']
            
            # --- 2. Annual Data (Fallback) ---
            a_stmt = ticker.income_stmt
            shares_annual = pd.Series(dtype=float)
            
            if a_stmt is not None and not a_stmt.empty:
                a_stmt = a_stmt.T
                a_stmt.index = pd.to_datetime(a_stmt.index).tz_localize(None).normalize()
                a_stmt.sort_index(inplace=True)
                
                if 'Basic Average Shares' in a_stmt.columns:
                    shares_annual = a_stmt['Basic Average Shares']

            # --- 3. Merge ---
            if shares_quarterly.empty and shares_annual.empty:
                 return pd.DataFrame()
            
            combined_index = shares_quarterly.index.union(shares_annual.index).sort_values()
            combined_shares = pd.Series(index=combined_index, dtype=float)
            
            combined_shares.update(shares_annual)
            combined_shares.update(shares_quarterly)
            
            # --- 4. Align with Market Data ---
            market_index_naive = market_data.index.tz_localize(None).normalize()
            full_index = market_index_naive.union(combined_shares.index).sort_values()
            
            aligned_shares = combined_shares.reindex(full_index).ffill().bfill()
            final_shares = aligned_shares.reindex(market_index_naive)
            final_shares.index = market_data.index # Restore TZ if any
            
            return final_shares.to_frame(name='Basic Average Shares')

        except Exception as e:
            print(f"Error fetching shares for {ticker_str}: {e}")
            return pd.DataFrame()

    def _fetch_revenue(self, ticker_str: str, market_data: pd.DataFrame) -> pd.DataFrame:
        try:
            ticker = yf.Ticker(ticker_str)
            
            # --- 1. Quarterly Data (Precise TTM) ---
            q_stmt = ticker.quarterly_income_stmt
            ttm_from_quarterly = pd.Series(dtype=float)
            
            if q_stmt is not None and not q_stmt.empty:
                q_stmt = q_stmt.T
                q_stmt.index = pd.to_datetime(q_stmt.index).tz_localize(None).normalize()
                q_stmt.sort_index(inplace=True)
                
                if 'Total Revenue' in q_stmt.columns:
                    # Calculate TTM: Sum of last 4 quarters
                    q_rev = q_stmt['Total Revenue']
                    ttm_from_quarterly = q_rev.rolling(window=4, min_periods=4).sum()
            
            # --- 2. Annual Data (Fallback History) ---
            a_stmt = ticker.income_stmt
            annual_revenue = pd.Series(dtype=float)
            
            if a_stmt is not None and not a_stmt.empty:
                a_stmt = a_stmt.T
                a_stmt.index = pd.to_datetime(a_stmt.index).tz_localize(None).normalize()
                a_stmt.sort_index(inplace=True)
                
                if 'Total Revenue' in a_stmt.columns:
                    annual_revenue = a_stmt['Total Revenue']
            
            # --- 3. Merge Strategies ---
            if ttm_from_quarterly.empty and annual_revenue.empty:
                return pd.DataFrame()

            # Combine indices
            combined_index = ttm_from_quarterly.index.union(annual_revenue.index).sort_values()
            
            # Create combined series
            # Priority: Use Quarterly TTM if available, else Annual
            combined_revenue = pd.Series(index=combined_index, dtype=float)
            
            # Fill with Annual first (base layer)
            combined_revenue.update(annual_revenue)
            
            # Overlay with Quarterly TTM (higher precision layer)
            combined_revenue.update(ttm_from_quarterly)
            
            # --- 4. Align with Market Data ---
            market_index_naive = market_data.index.tz_localize(None).normalize()
            
            # Union with market dates to allow forward filling interactions
            full_index = market_index_naive.union(combined_revenue.index).sort_values()
            aligned_rev = combined_revenue.reindex(full_index).ffill().bfill()
            
            # Filter back to only market days
            final_rev = aligned_rev.reindex(market_index_naive)
            final_rev.index = market_data.index # Restore timestamps
            
            return final_rev.to_frame(name='Total Revenue')

        except Exception as e:
            print(f"Error fetching revenue for {ticker_str}: {e}")
            return pd.DataFrame()


    def _fetch_market_data(self, ticker_str: str, period: str) -> pd.DataFrame:
        try:
            ticker = yf.Ticker(ticker_str)
            history = ticker.history(period=period, auto_adjust=False)

            price_data = history[['Adj Close']]

            return price_data.sort_index()
        except Exception as e:
            print(f"Error fetching market data for {ticker}: {e}")
            return pd.DataFrame()
