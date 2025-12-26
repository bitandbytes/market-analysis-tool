from PyQt6.QtWidgets import QComboBox, QStyledItemDelegate
from PyQt6.QtGui import QPalette, QStandardItem
from PyQt6.QtCore import Qt, QEvent

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None, placeholder_text="Select Analysis Modules..."):
        super(CheckableComboBox, self).__init__(parent)
        self._checked_items = []
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(self.model())
        self.view().viewport().installEventFilter(self)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText(placeholder_text)

    def eventFilter(self, widget, event):
        if widget == self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.view().indexAt(event.pos())
            item = self.model().item(index.row())
            if item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
                if item.text() in self._checked_items:
                    self._checked_items.remove(item.text())
            else:
                item.setCheckState(Qt.CheckState.Checked)
                if item.text() not in self._checked_items:
                    self._checked_items.append(item.text())
            self.updateText()
            return True
        return super().eventFilter(widget, event)

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.CheckState.Checked:
            item.setCheckState(Qt.CheckState.Unchecked)
            if item.text() in self._checked_items:
                self._checked_items.remove(item.text())
        else:
            item.setCheckState(Qt.CheckState.Checked)
            if item.text() not in self._checked_items:
                self._checked_items.append(item.text())
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

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def checkedItems(self):
        return list(self._checked_items)

    def updateText(self):
        items = self.checkedItems()
        text = ", ".join(items) if items else ""
        self.lineEdit().setText(text)

    def hidePopup(self):
        super().hidePopup()
        self.updateText()
