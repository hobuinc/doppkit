import logging
from qtpy import QtCore, QtWidgets

from typing import Optional

logger = logging.getLogger("doppkit")


class MagicLinkDialog(QtWidgets.QDialog):
	
	magicLinkText = QtCore.Signal(object)

	def __init__(self, parent: Optional[QtWidgets.QWidget]=None) -> None:
		super().__init__(parent)

		self.lineEdit = QtWidgets.QLineEdit()
		label = QtWidgets.QLabel("&Magic Link Text")
		label.setBuddy(self.lineEdit)

		labelFont = label.font()
		labelFont.setPointSize(10)
		label.setFont(labelFont)

		standardButton = QtWidgets.QDialogButtonBox.StandardButton
		self.buttonBox = QtWidgets.QDialogButtonBox(
			standardButton.Ok | standardButton.Close,
			QtCore.Qt.Orientation.Horizontal
		)
		self.buttonBox.accepted.connect(self.passMagicLinkText)
		self.buttonBox.rejected.connect(self.cancel)

		layout = QtWidgets.QVBoxLayout()
		layout.addWidget(label)
		layout.addWidget(self.lineEdit)
		layout.addWidget(self.buttonBox)
		self.setLayout(layout)
		self.setWindowTitle("Magic Link Dialog")

	@QtCore.Slot()
	def passMagicLinkText(self):
		self.magicLinkText.emit(self.lineEdit.text())
		self.lineEdit.clear()
		self.close()

	@QtCore.Slot()
	def cancel(self):
		self.lineEdit.clear()
		self.close()
