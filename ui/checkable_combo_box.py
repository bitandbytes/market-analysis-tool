from PySide6.QtWidgets import QComboBox, QStyledItemDelegate, QListView, QStyle, QStyleOptionButton, QApplication
from PySide6.QtGui import QPalette, QStandardItem, QFontMetrics, QMouseEvent
from PySide6.QtCore import Qt, QEvent, QRect, QPoint, QSize, Signal

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None, placeholder_text="Select Analysis Modules..."):
        super(CheckableComboBox, self).__init__(parent)
        self._checked_items = []
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(self.model())
        self.model().dataChanged.connect(self.onDataChanged)
        self.view().viewport().installEventFilter(self)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText(placeholder_text)

    def eventFilter(self, widget, event):
        if widget == self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.view().indexAt(event.pos())
            item = self.model().item(index.row())
            if item and item.isEnabled(): # Check if enabled (skip separators)
                if item.checkState() == Qt.CheckState.Checked:
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    item.setCheckState(Qt.CheckState.Checked)
                return True
        return super().eventFilter(widget, event)

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.isEnabled(): # Check if enabled
            if item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)

    def onDataChanged(self, topLeft, bottomRight, roles):
        if not roles or Qt.ItemDataRole.CheckStateRole in roles:
            for row in range(topLeft.row(), bottomRight.row() + 1):
                item = self.model().item(row)
                
                # Skip separators (which don't have checkbox flags usually, or we check enabled)
                if not item.isEnabled(): 
                    continue

                text = item.text()
                if item.checkState() == Qt.CheckState.Checked:
                    if text not in self._checked_items:
                        self._checked_items.append(text)
                else:
                    if text in self._checked_items:
                        self._checked_items.remove(text)
            self.updateText()

    def addItem(self, text, userData=None, tooltip=None):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        if tooltip:
            item.setToolTip(tooltip)
        self.model().appendRow(item)
        if userData is not None:
            item.setData(userData)

    def addSeparator(self, text):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags) # Disable everything
        # Make it look like a header (bold, maybe distinct color)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        # item.setBackground(QPalette().mid()) # Optional: Grey background
        self.model().appendRow(item)

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def checkedItems(self):
        return list(self._checked_items)

    def clear(self):
        self._checked_items = []
        self.model().removeRows(0, self.model().rowCount())
        self.hidePopup()

    def updateText(self):
        items = self.checkedItems()
        text = ", ".join(items) if items else ""
        self.lineEdit().setText(text)

    def hidePopup(self):
        super().hidePopup()
        self.updateText()
