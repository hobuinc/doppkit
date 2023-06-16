from PySide6 import QtCore, QtGui, QtWidgets
import sys

class Validator(QtGui.QValidator):

    def validate(self, index_, pos):
        return (QtGui.QValidator.State.Acceptable, index_, pos)

if __name__ == "__main__":
    qApp = QtWidgets.QApplication(sys.argv)

    lineEdit = QtWidgets.QLineEdit()
    validator = Validator()
    lineEdit.setValidator(validator)
    lineEdit.show()
    qApp.exec()