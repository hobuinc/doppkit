import typing


from qtpy.QtCore import Slot
from qtpy.QtWidgets import QAction, QApplication, QMenu, QMenuBar, QMainWindow

class MenuBar(QMenuBar):

    def __init__(self) -> None:
        # intentionally do not pass a parent to the menu bar...
        super().__init__(None)
        # self.setNativeMenuBar(False)
        self.fileMenu = QMenu("File", self)
        self.viewMenu = ViewMenu(self)
        self.helpMenu = QMenu("Help", self)

        for menu in [self.fileMenu, self.viewMenu, self.helpMenu]:
            self.addMenu(menu)


class ViewMenu(QMenu):

    def __init__(self, title: typing.Optional[str] = None, parent: MenuBar = None) -> None:
        if isinstance(title, str):
            super().__init__(title, parent)
        else:
            super().__init__(parent)
        self.setTitle("View")
        self.viewLogAction()

    def viewLogAction(self) -> None:
        invokeLogAction = QAction("Show Log", self)
        invokeLogAction.setStatusTip("View Log")
        invokeLogAction.triggered.connect(self.invokeLog)
        self.addAction(invokeLogAction)

    @Slot()
    def invokeLog(self) -> None:
        for widget in QApplication.instance().topLevelWidgets():
            if isinstance(widget, QMainWindow):
                break
        else:
            raise RuntimeError("Main Window not found, how did this happen?")
        
        if hasattr(widget, 'logView'):
            widget.logView.show()
