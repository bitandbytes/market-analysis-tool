import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow

# Mock plugins and data
class MockDataSource:
    def fetch_data(self, ticker_str: str, period: str = "1y") -> Tuple[pd.DataFrame, pd.DataFrame]:
        dates = pd.date_range(start="2023-01-01", periods=100)
        data = pd.DataFrame({
            "Close": np.random.rand(100) * 100,
            "Volume": np.random.randint(100, 1000, 100)
        }, index=dates)
        # Ensure we return a non-empty DataFrame for financials to avoid "No data" warning/checks
        financials = pd.DataFrame({"Revenue": [100, 200]}, index=[2023, 2024]) 
        return data, financials

class MockAnalysisPlugin:
    def get_name(self):
        return "Mock Analysis"
        
    def analyze(self, ticker, financials, market_data):
        # Return simple data simulating a result
        return {
            "chart_data": market_data['Close']
        }

class MockPluginManager:
    def discover_plugins(self):
        pass
    def get_all_data_sources(self):
        return ["Mock Source"]
    def get_all_analysis_plugins(self):
        return ["Mock Analysis"]
    def get_data_source(self, name):
        return MockDataSource()
    def get_analysis_plugin(self, name):
        return MockAnalysisPlugin()

class TestSeabornPlotting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication if it doesn't exist
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Patch PluginManager
        self.pm_patcher = patch('ui.main_window.PluginManager', MockPluginManager)
        self.pm_patcher.start()
        
        self.window = MainWindow()
        
    def tearDown(self):
        self.pm_patcher.stop()
        self.window.close()

    def test_plotting_logic(self):
        # 1. Setup UI state
        # Select ticker
        model = self.window.tickers.model()
        if model.rowCount() > 0:
            model.item(0).setCheckState(Qt.CheckState.Checked) # Checked
        else:
            # Add a mock ticker if none (depends on tickers.txt existence)
            self.window.tickers.addItem("MOCK")
            model.item(0).setCheckState(Qt.CheckState.Checked)
            
        # Select Analysis
        self.window.analysis_combo.model().item(0).setCheckState(Qt.CheckState.Checked)
        
        # 2. Run Analysis
        print("Running analysis...")
        self.window.run_analysis()
        
        # 3. Verify Plot
        # Check if the central chart widget has plots
        
        if hasattr(self.window, 'canvas'):
            figure = self.window.canvas.figure
            axes = figure.axes
            self.assertTrue(len(axes) > 0, "No axes created in figure")
            print(f"Verified {len(axes)} axes in figure.")
            
            # Check if lines are plotted
            lines = axes[0].get_lines()
            self.assertTrue(len(lines) > 0, "No lines plotted on axis 0")
            print(f"Verified {len(lines)} lines on first axis.")
        else:
             self.fail("window.canvas not found, refactor seemingly not applied or incorrect field name.")

if __name__ == "__main__":
    unittest.main()
