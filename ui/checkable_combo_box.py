from PyQt6.QtWidgets import QComboBox, QStyledItemDelegate
from PyQt6.QtGui import QPalette, QStandardItem
from PyQt6.QtCore import Qt, QEvent

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None, placeholder_text="Select Analysis Modules..."):
        super(CheckableComboBox, self).__init__(parent)
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
            else:
                item.setCheckState(Qt.CheckState.Checked)
            self.updateText()
            return True
        return super().eventFilter(widget, event)

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.CheckState.Checked:
            item.setCheckState(Qt.CheckState.Unchecked)
        else:
            item.setCheckState(Qt.CheckState.Checked)
        self.updateText()

    def addItem(self, text, userData=None):
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)
        if userData is not None:
            item.setData(userData)

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def checkedItems(self):
        checkedItems = []
        for i in range(self.count()):
            item = self.model().item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checkedItems.append(item.text())
        return checkedItems

    def updateText(self):
        items = self.checkedItems()
        text = ", ".join(items) if items else ""
        self.lineEdit().setText(text)

    def hidePopup(self):
        super().hidePopup()
        self.updateText()
