import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QListWidget, 
                             QListWidgetItem, QMessageBox, QSplitter, QFrame, QSpinBox, QStyle, QFileDialog)
from PySide6.QtGui import QPalette, QStandardItem, QFontMetrics, QMouseEvent, QAction
from PySide6.QtCore import Qt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.colors
from PySide6.QtWebEngineWidgets import QWebEngineView

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
        
        # --- Menu Bar ---
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        
        load_tickers_action = QAction("Load Tickers...", self)
        load_tickers_action.triggered.connect(self.load_tickers_from_file)
        file_menu.addAction(load_tickers_action)
        
        # Main Layout: Splitter (Left: Controls, Right: Charts)
        layout = QHBoxLayout(main_widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # --- Left Panel: Controls ---
        controls_panel = QFrame()
        controls_layout = QVBoxLayout(controls_panel)
        
        # Ticker Input
        tickers = []
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.getcwd()
            
            ticker_path = os.path.join(base_path, "ui", "tickers.txt")
            
            with open(ticker_path, "r") as ticker_file:
                 tickers = ticker_file.read().splitlines()
        except Exception as e:
            print(f"Error loading tickers: {e}")
            tickers = ["AAPL", "GOOGL", "MSFT"]

        self.tickers = CheckableComboBox(placeholder_text="Select Tickers...")
        self.tickers.setMaxVisibleItems(30)
        self._populate_tickers(tickers)
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
        self.period_spin.setValue(4)
        self.period_spin.setSuffix(" year(s)")
        controls_layout.addWidget(self.period_spin)

        # Analysis Selection
        controls_layout.addWidget(QLabel("Analysis Modules:"))
        self.analysis_combo = CheckableComboBox(placeholder_text="Select Analysis Modules...")
        self.analysis_combo.setMaxVisibleItems(15)
        
        # Dynamic Grouping
        all_plugins = self.plugin_manager.get_all_analysis_plugins()
        groups = {}
        
        for name in all_plugins:
            plugin = self.plugin_manager.get_analysis_plugin(name)
            
            # Safe access to category (in case of legacy plugins or issues)
            category = "General"
            if hasattr(plugin, 'get_category'):
                try:
                    category = plugin.get_category()
                except:
                    pass
            
            if category not in groups:
                 groups[category] = []
            groups[category].append((name, plugin))
            
        # Define specific order for known categories if desired
        # Or just sort alphabetically
        sorted_categories = sorted(groups.keys())
        
        # Move "General" to end or specific spot?
        # Let's just do: Valuation Ratios, Price vs Fundamentals, General (if we want specific order, we can force it)
        # For now, simple alphabetical or priority list
        priority_order = ["General", "Price vs Fundamentals", "Valuation Ratios"]
        
        # Sort keys based on priority, then alphabet
        def sort_key(k):
             if k in priority_order:
                 return priority_order.index(k)
             return 999 # Others at end

        sorted_categories = sorted(groups.keys(), key=sort_key)

        for category in sorted_categories:
            self.analysis_combo.addSeparator(f"{category}")
            
            # Sort items within category
            items = sorted(groups[category], key=lambda x: x[0])
            
            for name, plugin in items:
                 description = plugin.get_description() if hasattr(plugin, 'get_description') else ""
                 self.analysis_combo.addItem(name, tooltip=description)
                 
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
    
    def _populate_tickers(self, tickers):
        for ticker in tickers:
            if ticker.startswith("#"):
                self.tickers.addSeparator(ticker.lstrip("#").lstrip(" "))
            else:
                self.tickers.addItem(ticker)

    def load_tickers_from_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Ticker File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    content = f.read()
                    
                # Parse tickers: split by newlines, strip whitespace, remove empty
                new_tickers = [line.strip() for line in content.splitlines() if line.strip()]
                
                if new_tickers:
                    # Update the ComboBox
                    self.tickers.clear()
                    self._populate_tickers(new_tickers)
                    self.statusBar().showMessage(f"Loaded {len(new_tickers)} tickers from {os.path.basename(file_name)}")
                else:
                    self.statusBar().showMessage("No valid tickers found in file.")
                    self.show_warning("Empty File", "No valid tickers found in file.")
                    
            except Exception as e:
                self.statusBar().showMessage(f"Error: {e}")
                self.show_error("File Error", f"Could not read file: {e}")

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
        for ticker_item in selected_tickers:
            try:
                ticker = ticker_item.split(" -")[0].strip()
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
                        # Handle DataFrame (multiple lines) or Series (single line)
                        if isinstance(chart_data, pd.Series):
                            chart_data = chart_data.to_frame(name=f"{ticker}")
                        
                        # Use slightly different dash styles for different columns if multiple
                        dash_styles = ['solid', 'dash', 'dot', 'dashdot']
                        
                        for col_idx, col_name in enumerate(chart_data.columns):
                            # Construct label: "Ticker" or "Ticker - Column"
                            label = f"{ticker}" if len(chart_data.columns) == 1 else f"{ticker} - {col_name}"
                            
                            # Add Trace
                            fig.add_trace(go.Scatter(
                                x=chart_data.index, 
                                y=chart_data[col_name],
                                mode='lines',
                                name=label,
                                legendgroup=ticker,
                                line=dict(
                                    color=colors[j % len(colors)],
                                    dash=dash_styles[col_idx % len(dash_styles)]
                                ),
                                showlegend=True # (i==0) logic was hiding legends for subsequent traces on multi-plot, let's show all or smart filter
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
