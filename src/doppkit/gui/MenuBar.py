import typing


from qtpy.QtCore import Slot
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QAction, QApplication, QMenu, QMenuBar, QMainWindow

from .SettingsDialog import SettingsDialog

class MenuBar(QMenuBar):

    def __init__(self) -> None:
        # intentionally do not pass a parent to the menu bar...
        super().__init__(None)

        for widget in QApplication.instance().topLevelWidgets():
            if isinstance(widget, QMainWindow):
                self.mainWindow = widget
                break
        else:
            raise RuntimeError("Main Window not Found")
        self.fileMenu = FileMenu(self)
        self.viewMenu = ViewMenu(self)
        self.helpMenu = QMenu("Help", self)

        for menu in [self.fileMenu, self.viewMenu, self.helpMenu]:
            self.addMenu(menu)

        self.settingsDialog: typing.Optional[SettingsDialog] = None

class FileMenu(QMenu):

    def __init__(self, title: typing.Optional[str] = None, parent: MenuBar = None) -> None:
        if isinstance(title, str):
            super().__init__(title, parent)
        else:
            parent, title = title, ""
            super().__init__(parent)
        self.setTitle("File")
        self.settingsDialog: typing.Optional['SettingsDialog'] = None
        self._settingsAction()
        self._quitAction()

    def _settingsAction(self) -> None:
        settingsAction = QAction("Preferences", self)
        settingsAction.setStatusTip("Settings")
        settingsAction.setMenuRole(QAction.MenuRole.PreferencesRole)
        settingsAction.triggered.connect(self.invokeSettings)
        self.addAction(settingsAction)

    @Slot()
    def invokeSettings(self):
        if self.settingsDialog is None:
            self.settingsDialog = SettingsDialog(self)
            self.settingsDialog.rejected.connect(self._resetSettingsDialog)
            self.settingsDialog.show()
    
    @Slot()
    def _resetSettingsDialog(self) -> None:
        self.settingsDialog = None

    def _quitAction(self) -> None:
        quitAction = QAction("Quit", self)
        quitAction.setStatusTip("Quit")
        quitAction.triggered.connect(QApplication.instance().quit)
        quitAction.setShortcut(QKeySequence.StandardKey.Quit)
        quitAction.setMenuRole(QAction.MenuRole.QuitRole)
        self.addAction(quitAction)




class ViewMenu(QMenu):

    def __init__(self, title: typing.Optional[str] = None, parent: MenuBar = None) -> None:
        if isinstance(title, str):
            super().__init__(title, parent)
        else:
            parent, title = title, ""
            super().__init__(parent)
        self.setTitle("View")
        self._viewLogAction()

    def _viewLogAction(self) -> None:
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
