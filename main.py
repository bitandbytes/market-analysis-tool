import sys
import os

# Add project root to path to allow absolute imports
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

from PyQt6.QtGui import QIcon
import os

def main():
    app = QApplication(sys.argv)
    
    # Set App Icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")
    app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
