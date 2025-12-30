from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict, Any, Optional

class DataSourceInterface(ABC):
    """Interface for data source plugins."""

    @abstractmethod
    def get_name(self) -> str:
        """Returns the name of the data source."""
        pass

    @abstractmethod
    def fetch_data(self, ticker_str: str, period: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetches both market data and financials.
        Returns (market_data, financials).
        """
        pass

class AnalysisPluginInterface(ABC):
    """Interface for analysis plugins."""

    @abstractmethod
    def get_name(self) -> str:
        """Returns the name of the analysis module."""
        pass

    @abstractmethod
    def analyze(self, ticker: str, financials: pd.DataFrame, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Performs analysis on the provided data.
        Returns a dictionary containing:
        - 'chart_data': (optional) data suitable for plotting
        - 'summary': str (optional) text summary
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Returns a description of the analysis module, 
        including calculation method and interpretation guide.
        """
        pass

    @abstractmethod
    def get_category(self) -> str:
        """
        Returns the category of the analysis module for grouping in the UI.
        Examples: "Valuation Ratios", "Price vs Fundamentals", "General"
        """
        pass
