import sys
import pandas as pd
import numpy as np
import seaborn as sns
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QListWidget, 
                             QListWidgetItem, QMessageBox, QSplitter, QFrame, QSpinBox, QStyle)
from PyQt6.QtCore import Qt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.colors
from PyQt6.QtWebEngineWidgets import QWebEngineView

from core.plugin_manager import PluginManager
from ui.checkable_combo_box import CheckableComboBox

class MainWindow(QMainWindow):
    CHART_HEIGHT_PER_MODULE = 500
    MAX_SUBPLOTS = 2

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
        self.tickers = CheckableComboBox(placeholder_text="Select Tickers...")
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
        self.analysis_combo = CheckableComboBox(placeholder_text="Select Analysis Modules...")
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
        
        # WebEngineView for Plotly
        self.browser = QWebEngineView()
        self.chart_layout.addWidget(self.browser)
        
        splitter.addWidget(self.chart_panel)
        splitter.setSizes([300, 900])

        self.statusBar().showMessage(f"Ready")

    def show_warning(self, title, message):
        self.statusBar().showMessage(f"Warning: {message}")
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        # Force the standard warning icon
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        msg.setIconPixmap(icon.pixmap(64, 64))
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def show_error(self, title, message):
        self.statusBar().showMessage(f"Error: {message}")
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        # Force the standard warning icon
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
        msg.setIconPixmap(icon.pixmap(64, 64))
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def run_analysis(self):
        self.statusBar().showMessage(f"Please wait...")
        selected_tickers = self.tickers.checkedItems()
        if not selected_tickers:
            self.show_warning("Input Error", "Please select at least one ticker symbol.")
            return

        source_name = self.source_combo.currentText()
        data_source = self.plugin_manager.get_data_source(source_name)
        
        if not data_source:
            self.show_error("Error", "Selected data source not found.")
            return

        # Get Period
        period_years = self.period_spin.value()
        period_str = f"{period_years}y"

        # Run Selected Analyses
        selected_analyses = self.analysis_combo.checkedItems()
        if not selected_analyses:
            self.show_warning("Selection Error", "Please select at least one analysis module.")
            return

        # Create Plotly Figure with Subplots
        fig = make_subplots(rows=len(selected_analyses), cols=1, 
                            shared_xaxes=True, 
                            vertical_spacing=0.1,
                            subplot_titles=selected_analyses)
                            
        # Colors for different tickers
        colors = plotly.colors.qualitative.Plotly * 10
        
        self.statusBar().showMessage(f"Fetching data...")
        QApplication.processEvents()
        
        # Cache data
        data_cache = {}
        for ticker in selected_tickers:
            try:
                market_data, financials = data_source.fetch_data(ticker, period=period_str)
                if not financials.empty and not market_data.empty:
                    data_cache[ticker] = (market_data, financials)
                else:
                    print(f"Warning: No data for {ticker}")
                    self.statusBar().showMessage(f"Warning: No data for {ticker}")
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
                self.statusBar().showMessage(f"Error fetching data for {ticker}: {e}")

        if not data_cache:
            self.show_warning("Data Error", "Could not fetch data for any selected tickers.")
            return

        for i, plugin_name in enumerate(selected_analyses):
            plugin = self.plugin_manager.get_analysis_plugin(plugin_name)
            
            for j, (ticker, (market_data, financials)) in enumerate(data_cache.items()):
                try:
                    results = plugin.analyze(ticker, financials, market_data)
                    
                    if not results:
                        print(f"Analysis Error ({plugin_name} - {ticker})")
                        self.statusBar().showMessage(f"Analysis Error ({plugin_name} - {ticker})")
                        continue
                    
                    chart_data = results.get('chart_data')
                    if chart_data is not None:
                         # Add Trace
                        fig.add_trace(go.Scatter(
                            x=chart_data.index, 
                            y=chart_data.values.flatten(),
                            mode='lines',
                            name=f"{ticker}",
                            legendgroup=ticker,
                            line=dict(color=colors[j % len(colors)]),
                            showlegend=(i==0)
                        ), row=i+1, col=1)
                
                except Exception as e:
                    print(f"Error running {plugin_name} for {ticker}: {e}")
                    self.statusBar().showMessage(f"Error running {plugin_name} for {ticker}")

        layout_args = {
            "template": "plotly_white",
            "hovermode": "x unified"
        }
        
        # Dynamic sizing: Autosize if <= 2 plots, otherwise fixed height per plot
        if len(selected_analyses) > self.MAX_SUBPLOTS:
            layout_args["height"] = self.CHART_HEIGHT_PER_MODULE * len(selected_analyses)
            
        fig.update_layout(**layout_args)
        
        html = fig.to_html(include_plotlyjs='cdn')
        self.browser.setHtml(html)
        
        self.statusBar().showMessage(f"Ready")
