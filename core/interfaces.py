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
    def fetch_data(self, ticker: str, period: str = "5y") -> tuple[pd.DataFrame, pd.DataFrame]:
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
        - 'metrics': pd.DataFrame or dict of calculated values
        - 'chart_data': (optional) data suitable for plotting
        - 'summary': str (optional) text summary
        """
        pass
