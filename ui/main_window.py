import sys
import pandas as pd
import numpy as np
import seaborn as sns
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QListWidget, 
                             QListWidgetItem, QMessageBox, QSplitter, QFrame, QSpinBox)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
from pyqtgraph import DateAxisItem

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
        
        # PyQtGraph Widget
        self.chart_widget = pg.GraphicsLayoutWidget()
        self.chart_widget.setBackground('w') # White background
        self.chart_layout.addWidget(self.chart_widget)
        
        splitter.addWidget(self.chart_panel)
        splitter.setSizes([300, 900])

    def run_analysis(self):
        self.statusBar().showMessage(f"Please wait...")
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

        self.chart_widget.clear()
        
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

        # Colors for different tickers using Seaborn
        # Generate distinct colors
        n_colors = max(len(data_cache), 1)
        palette = sns.color_palette("husl", n_colors)
        # Convert to 0-255 RGB for PyQtGraph
        colors = [(int(r*255), int(g*255), int(b*255)) for r, g, b in palette]

        for i, plugin_name in enumerate(selected_analyses):
            plugin = self.plugin_manager.get_analysis_plugin(plugin_name)
            
            # Create a plot area
            # Use DateAxisItem for x-axis
            axis = DateAxisItem(orientation='bottom')
            p = self.chart_widget.addPlot(row=i, col=0, axisItems={'bottom': axis}, title=plugin_name)
            p.showGrid(x=True, y=True)
            p.addLegend()
            
            # Crosshair Lines
            vLine = pg.InfiniteLine(angle=90, movable=False)
            hLine = pg.InfiniteLine(angle=0, movable=False)
            p.addItem(vLine, ignoreBounds=True)
            p.addItem(hLine, ignoreBounds=True)
            
            # Store data for crosshair lookup
            plot_data = {}

            for j, (ticker, (market_data, financials)) in enumerate(data_cache.items()):
                try:
                    results = plugin.analyze(ticker, financials, market_data)
                    
                    if "error" in results:
                        print(f"Analysis Error ({plugin_name} - {ticker}): {results['error']}")
                        continue
                    
                    # Plot
                    chart_data = results.get('chart_data')
                    if chart_data is not None:
                        # Convert index (datetime) to timestamp for PyQtGraph
                        x = [t.timestamp() for t in chart_data.index]
                        y = chart_data.values.flatten() # Ensure 1D array
                        
                        color = colors[j % len(colors)]
                        # Increased width to 3
                        p.plot(x, y, pen=pg.mkPen(color, width=3), name=ticker)
                        
                        # Store for crosshair
                        plot_data[ticker] = (x, y)
                
                except Exception as e:
                    print(f"Error running {plugin_name} for {ticker}: {e}")

            # Crosshair Mouse Move Handler
            def mouseMoved(evt, plot=p, data=plot_data, title=plugin_name):
                pos = evt[0]
                if plot.sceneBoundingRect().contains(pos):
                    mousePoint = plot.vb.mapSceneToView(pos)
                    index = int(mousePoint.x())
                    
                    # Update lines
                    # Access vLine/hLine from closure or find them
                    # Better to pass them or use a class, but closure works for simple case
                    # We need to find the specific vLine/hLine for *this* plot
                    # Since we are in a loop, 'vLine' and 'hLine' variables are overwritten.
                    # We must capture them in the closure.
                    pass

            # To correctly capture vLine/hLine and update the specific plot, 
            # we need a factory or a separate method. 
            # Let's use a helper method to attach the crosshair to avoid closure issues.
            self.add_crosshair(p, vLine, hLine, plot_data, plugin_name)

        self.statusBar().showMessage(f"Analysis complete.")

    def add_crosshair(self, plot, vLine, hLine, plot_data, title_prefix):
        def mouseMoved(evt):
            pos = evt[0]
            if plot.sceneBoundingRect().contains(pos):
                mousePoint = plot.vb.mapSceneToView(pos)
                x_val = mousePoint.x()
                y_val = mousePoint.y()
                
                vLine.setPos(x_val)
                hLine.setPos(y_val)
                
                # Format Date
                date_str = datetime.fromtimestamp(x_val).strftime('%Y-%m-%d')
                
                # Build Label
                label_text = f"<span style='font-size: 12pt; font-weight: bold'>{title_prefix}</span><br>"
                label_text += f"<span style='color: black'>Date: {date_str}</span><br>"
                
                # Find nearest values
                for ticker, (x_data, y_data) in plot_data.items():
                    # Find nearest x index
                    # Assuming x_data is sorted
                    idx = (np.abs(np.array(x_data) - x_val)).argmin()
                    if 0 <= idx < len(y_data):
                        val = y_data[idx]
                        label_text += f"<span style='color: blue'>{ticker}: {val:.2f}</span><br>"
                
                # Update Title (using HTML for formatting)
                plot.setTitle(label_text)

        self.proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)
        # Note: We need to keep a reference to SignalProxy, otherwise it gets garbage collected.
        # Since we have multiple plots, we should store them in a list.
        if not hasattr(self, 'proxies'):
            self.proxies = []
        self.proxies.append(self.proxy)
