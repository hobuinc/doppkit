import asyncio

from qtpy import QtCore, QtGui, QtWidgets
import qasync
from doppkit.qt import Window
import importlib
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from doppkit import Application
def start_gui(app: 'Application'):
    qApp = QtWidgets.QApplication(sys.argv)
    qApp.setApplicationName("doppkit")
    qApp.setOrganizationName("Hobu")
    qApp.setStyle("fusion")

    icon = QtGui.QIcon(
        os.path.join(
            importlib.resources.files("doppkit.resources"),
            'grid-icon.ico'
        )
    )

    qApp.setWindowIcon(icon)
    window = Window(app)
    window.setWindowIcon(icon)

    # loop = qasync.QEventLoop(qApp)
    # asyncio.set_event_loop(loop)
    # with loop:
    #     loop.run_forever()
    sys.exit(qApp.exec_())

if __name__ == "__main__":
    from doppkit.app import gui
    gui()