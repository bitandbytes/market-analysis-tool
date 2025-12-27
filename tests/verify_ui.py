import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Add project root to path
sys.path.append(os.getcwd())

from ui.main_window import MainWindow
from ui.checkable_combo_box import CheckableComboBox
from core.plugin_manager import PluginManager

# Mock PluginManager to avoid dependency on actual plugins for this UI test
class MockPluginManager:
    def discover_plugins(self):
        pass
    def get_all_data_sources(self):
        return ["Mock Source"]
    def get_all_analysis_plugins(self):
        return ["Analysis A", "Analysis B", "Analysis C"]
    def get_data_source(self, name):
        return None
    def get_analysis_plugin(self, name):
        return None

def verify_ui():
    app = QApplication(sys.argv)
    
    # Patch PluginManager in main_window module or just mock it in the instance if possible.
    # Since MainWindow instantiates PluginManager in __init__, we need to patch it or mock it before.
    # But for simplicity, let's just let it run with actual PluginManager if it doesn't crash, 
    # or better, we can monkeypatch MainWindow's PluginManager usage if needed.
    # However, let's assume the actual PluginManager works fine or returns empty if no plugins.
    # To be safe and test our specific logic, let's monkeypatch the class used in MainWindow.
    
    import ui.main_window
    ui.main_window.PluginManager = MockPluginManager
    
    window = MainWindow()
    
    # 1. Check widget type
    if not isinstance(window.analysis_combo, CheckableComboBox):
        print("FAIL: analysis_combo is not CheckableComboBox")
        return
    print("PASS: analysis_combo is CheckableComboBox")
    
    # 2. Check population
    count = window.analysis_combo.count()
    if count != 3:
        print(f"FAIL: Expected 3 items, got {count}")
        return
    print("PASS: Items populated correctly")
    
    # 3. Check selection logic
    # Select "Analysis A" and "Analysis C"
    model = window.analysis_combo.model()
    model.item(0).setCheckState(Qt.CheckState.Checked)
    model.item(2).setCheckState(Qt.CheckState.Checked)
    
    checked = window.analysis_combo.checkedItems()
    expected = ["Analysis A", "Analysis C"]
    
    if checked != expected:
        print(f"FAIL: Expected {expected}, got {checked}")
        return
    print("PASS: Selection logic works")
    
    # 4. Check text update
    window.analysis_combo.updateText()
    text = window.analysis_combo.lineEdit().text()
    if text != "Analysis A, Analysis C":
        print(f"FAIL: Expected text 'Analysis A, Analysis C', got '{text}'")
        return
    print("PASS: Text update works")

    print("ALL TESTS PASSED")

if __name__ == "__main__":
    verify_ui()
