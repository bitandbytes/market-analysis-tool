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
            
            # Fetch Operating Cash Flow
            ocf_data = self._fetch_ocf(ticker_str, market_data)
            if not ocf_data.empty:
                financials['Operating Cash Flow'] = ocf_data.iloc[:, 0]
                
            # Fetch Capital Expenditure
            capex_data = self._fetch_capex(ticker_str, market_data)
            if not capex_data.empty:
                # yfinance often returns CapEx as negative (cash outflow). 
                # Ensure we handle it appropriately in downstream plugins (fcf_yield.py adds it).
                financials['Capital Expenditure'] = capex_data.iloc[:, 0]
            
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
        """
        Fetches Basic Average Shares.
        Uses _fetch_financial_metric with use_rolling_sum=False.
        """
        return self._fetch_financial_metric(
            ticker_str,
            market_data,
            metric_keys=['Basic Average Shares'],
            is_cashflow=False,
            col_name='Basic Average Shares',
            use_rolling_sum=False
        )

    def _fetch_revenue(self, ticker_str: str, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Fetches Total Revenue (TTM).
        Uses _fetch_financial_metric with use_rolling_sum=True.
        """
        return self._fetch_financial_metric(
            ticker_str,
            market_data,
            metric_keys=['Total Revenue'],
            is_cashflow=False,
            col_name='Total Revenue',
            use_rolling_sum=True
        )


    def _fetch_ocf(self, ticker_str: str, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Fetches Operating Cash Flow data.
        Tries 'Operating Cash Flow', then 'Total Cash From Operating Activities'.
        """
        potential_keys = ['Operating Cash Flow', 'Total Cash From Operating Activities']
        return self._fetch_financial_metric(
            ticker_str, 
            market_data, 
            metric_keys=potential_keys, 
            is_cashflow=True,
            col_name='Operating Cash Flow'
        )

    def _fetch_capex(self, ticker_str: str, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Fetches Capital Expenditure data.
        Tries 'Capital Expenditure', then 'Capital Expenditures'.
        """
        potential_keys = ['Capital Expenditure', 'Capital Expenditures']
        return self._fetch_financial_metric(
            ticker_str, 
            market_data, 
            metric_keys=potential_keys, 
            is_cashflow=True,
            col_name='Capital Expenditure'
        )

    def _fetch_financial_metric(self, ticker_str: str, market_data: pd.DataFrame, metric_keys: list, is_cashflow: bool = False, col_name: str = 'Metric', use_rolling_sum: bool = True) -> pd.DataFrame:
        """
        Generic helper to fetch a financial metric from quarterly (TTM) and annual reports.
        """
        try:
            ticker = yf.Ticker(ticker_str)
            
            # Select statement type
            if is_cashflow:
                q_stmt_raw = ticker.quarterly_cashflow
                a_stmt_raw = ticker.cashflow
            else:
                q_stmt_raw = ticker.quarterly_income_stmt
                a_stmt_raw = ticker.income_stmt
                
            # --- 1. Quarterly Data (Precise TTM) ---
            ttm_from_quarterly = pd.Series(dtype=float)
            
            if q_stmt_raw is not None and not q_stmt_raw.empty:
                q_stmt = q_stmt_raw.T
                q_stmt.index = pd.to_datetime(q_stmt.index).tz_localize(None).normalize()
                q_stmt.sort_index(inplace=True)
                
                # Find valid column
                valid_key = next((k for k in metric_keys if k in q_stmt.columns), None)
                
                if valid_key:
                    q_metric = q_stmt[valid_key]
                    if use_rolling_sum:
                        # Calculate TTM: Sum of last 4 quarters
                        ttm_from_quarterly = q_metric.rolling(window=4, min_periods=4).sum()
                    else:
                        # Use raw quarterly value (e.g. for Shares)
                        ttm_from_quarterly = q_metric
            
            # --- 2. Annual Data (Fallback History) ---
            annual_metric = pd.Series(dtype=float)
            
            if a_stmt_raw is not None and not a_stmt_raw.empty:
                a_stmt = a_stmt_raw.T
                a_stmt.index = pd.to_datetime(a_stmt.index).tz_localize(None).normalize()
                a_stmt.sort_index(inplace=True)
                
                valid_key = next((k for k in metric_keys if k in a_stmt.columns), None)
                
                if valid_key:
                    annual_metric = a_stmt[valid_key]
            
            # --- 3. Merge Strategies ---
            if ttm_from_quarterly.empty and annual_metric.empty:
                return pd.DataFrame()

            # Combine indices
            combined_index = ttm_from_quarterly.index.union(annual_metric.index).sort_values()
            
            # Create combined series
            combined_series = pd.Series(index=combined_index, dtype=float)
            
            # Fill with Annual first (base layer)
            combined_series.update(annual_metric)
            
            # Overlay with Quarterly TTM (higher precision layer)
            combined_series.update(ttm_from_quarterly)
            
            # --- 4. Align with Market Data ---
            market_index_naive = market_data.index.tz_localize(None).normalize()
            
            # Union with market dates to allow forward filling interactions
            full_index = market_index_naive.union(combined_series.index).sort_values()
            aligned_metric = combined_series.reindex(full_index).ffill().bfill()
            
            # Filter back to only market days
            final_metric = aligned_metric.reindex(market_index_naive)
            final_metric.index = market_data.index # Restore timestamps
            
            return final_metric.to_frame(name=col_name)

        except Exception as e:
            print(f"Error fetching {col_name} for {ticker_str}: {e}")
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
