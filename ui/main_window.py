import sys
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QListWidget, 
                             QListWidgetItem, QMessageBox, QSplitter, QFrame, QSpinBox)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from core.plugin_manager import PluginManager
from ui.checkable_combo_box import CheckableComboBox

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Market Analysis Tool")
        self.resize(1200, 800)

        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main Layout: Splitter (Left: Controls, Right: Charts)
        layout = QHBoxLayout(main_widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # --- Left Panel: Controls ---
        controls_panel = QFrame()
        controls_layout = QVBoxLayout(controls_panel)
        
        # Ticker Input
        ticker_file = open("ui/tickers.txt", "r")
        tickers = ticker_file.read().splitlines()
        self.tickers = CheckableComboBox()
        self.tickers.addItems(tickers)
        controls_layout.addWidget(self.tickers)

        # Data Source Selection
        controls_layout.addWidget(QLabel("Data Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(self.plugin_manager.get_all_data_sources())
        controls_layout.addWidget(self.source_combo)

        # Evaluation Period Input
        controls_layout.addWidget(QLabel("Period (Years):"))
        self.period_spin = QSpinBox()
        self.period_spin.setRange(1, 20)
        self.period_spin.setValue(5)
        self.period_spin.setSuffix(" year(s)")
        controls_layout.addWidget(self.period_spin)

        # Analysis Selection
        controls_layout.addWidget(QLabel("Analysis Modules:"))
        self.analysis_combo = CheckableComboBox()
        self.analysis_combo.addItems(self.plugin_manager.get_all_analysis_plugins())
        controls_layout.addWidget(self.analysis_combo)

        # Run Button
        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.clicked.connect(self.run_analysis)
        controls_layout.addWidget(self.run_btn)
        
        controls_layout.addStretch()
        splitter.addWidget(controls_panel)

        # --- Right Panel: Charts ---
        self.chart_panel = QFrame()
        self.chart_layout = QVBoxLayout(self.chart_panel)
        
        # Matplotlib Figure
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.chart_layout.addWidget(self.canvas)
        
        splitter.addWidget(self.chart_panel)
        splitter.setSizes([300, 900])

    def run_analysis(self):
        selected_tickers = self.tickers.checkedItems()
        if not selected_tickers:
            QMessageBox.warning(self, "Input Error", "Please select at least one ticker symbol.")
            return

        source_name = self.source_combo.currentText()
        data_source = self.plugin_manager.get_data_source(source_name)
        
        if not data_source:
             QMessageBox.critical(self, "Error", "Selected data source not found.")
             return

        # Get Period
        period_years = self.period_spin.value()
        period_str = f"{period_years}y"

        # Run Selected Analyses
        selected_analyses = self.analysis_combo.checkedItems()
        if not selected_analyses:
            QMessageBox.warning(self, "Selection Error", "Please select at least one analysis module.")
            return

        self.figure.clear()
        # Create subplots based on number of selected analyses
        num_plots = len(selected_analyses)
        axes = self.figure.subplots(num_plots, 1, sharex=True)
        if num_plots == 1:
            axes = [axes]
        
        # Cache data to avoid refetching for each analysis
        data_cache = {}

        self.statusBar().showMessage(f"Fetching data...")
        QApplication.processEvents()

        for ticker in selected_tickers:
            try:
                market_data, financials = data_source.fetch_data(ticker, period=period_str)
                if not financials.empty and not market_data.empty:
                    data_cache[ticker] = (market_data, financials)
                else:
                    print(f"Warning: No data for {ticker}")
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")

        if not data_cache:
            QMessageBox.warning(self, "Data Error", "Could not fetch data for any selected tickers.")
            self.statusBar().showMessage("Ready")
            return

        for i, plugin_name in enumerate(selected_analyses):
            plugin = self.plugin_manager.get_analysis_plugin(plugin_name)
            ax = axes[i]
            
            for ticker, (market_data, financials) in data_cache.items():
                try:
                    results = plugin.analyze(ticker, financials, market_data)
                    
                    if "error" in results:
                        print(f"Analysis Error ({plugin_name} - {ticker}): {results['error']}")
                        continue
                    
                    # Plot
                    chart_data = results.get('chart_data')
                    if chart_data is not None:
                        ax.plot(chart_data.index, chart_data.values, label=f"{ticker}")
                
                except Exception as e:
                    print(f"Error running {plugin_name} for {ticker}: {e}")
            
            ax.set_title(f"{plugin_name}")
            ax.legend()
            ax.grid(True)

        self.figure.tight_layout()
        self.canvas.draw()
        self.statusBar().showMessage(f"Analysis complete.")
