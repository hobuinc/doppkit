from qtpy import QtCore, QtGui, QtWidgets


class ExportDelegate(QtWidgets.QStyledItemDelegate):

    def __int__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        pass


