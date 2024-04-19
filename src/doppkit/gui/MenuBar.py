import os
import typing


from qtpy.QtCore import Slot, QDir
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QAction, QApplication, QFileDialog, QMenu, QMenuBar, QMainWindow

from .SettingsDialog import SettingsDialog
from .MagicLinkDialog import MagicLinkDialog

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
        self.fileMenu = FileMenu(parent=self)
        self.viewMenu = ViewMenu(parent=self)
        self.helpMenu = QMenu("Help", self)

        for menu in [self.fileMenu, self.viewMenu, self.helpMenu]:
            self.addMenu(menu)


class FileMenu(QMenu):

    def __init__(
        self,
        title: typing.Optional[str] = None,
        parent: typing.Optional[MenuBar] = None
    ) -> None:
        if title is None:
            title = ""
        super().__init__(title, parent)
        self.setTitle("File")
        self.settingsDialog: typing.Optional['SettingsDialog'] = None
        self.magicLinkDialog: typing.Optional['MagicLinkDialog'] = None
        self._settingsAction()
        self._uploadFileAction()
        self._uploadDirectoryAction()
        self._provideMagicLinkAction()
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
    def invokeMagicLinkDialog(self):
        if self.magicLinkDialog is None:
            self.magicLinkDialog = MagicLinkDialog(parent=self)
            mainWindow = self.parent().mainWindow
            self.magicLinkDialog.magicLinkText.connect(mainWindow.parseMagicLink)
        self.magicLinkDialog.show()

    @Slot()
    def uploadFileDialog(self):
        filename, filter_ = QFileDialog.getOpenFileName(
            self,
            "Upload File",
            QDir.home().absolutePath(),
            options=QFileDialog.Option.ReadOnly
        )

        if filename is None:
            # user cancelled, abort
            return None

        for widget in QApplication.instance().topLevelWidgets():
            if isinstance(widget, QMainWindow):
                break
        else:
            raise RuntimeError("Main Window not found, how did this happen?")

        if hasattr(widget, 'uploadFiles'):
            widget.uploadFiles([filename])


    @Slot()
    def uploadDirectoryDialog(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Upload Directory",
            QDir.home().absolutePath(),
            options=QFileDialog.Option.ReadOnly
        )


        if directory == "":
            # user cancelled, abort
            return None

        files_to_upload = []
        for root, dirs, files in os.walk(directory):
            files_to_upload.extend(
                [
                    os.path.join(root, file_)
                    for file_ in files
                    if not file_.startswith(".")
                ]
            )

        for widget in QApplication.instance().topLevelWidgets():
            if isinstance(widget, QMainWindow):
                break
        else:
            raise RuntimeError("Main Window not found, how did this happen?")

        if hasattr(widget, 'uploadFiles'):
            widget.uploadFiles(files_to_upload, directory=directory)
    
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


    def _uploadFileAction(self):
        uploadFileAction = QAction("Upload File", self)
        uploadFileAction.setStatusTip("Upload File")
        uploadFileAction.triggered.connect(self.uploadFileDialog)
        self.addAction(uploadFileAction)

    def _uploadDirectoryAction(self):
        uploadDirectoryAction = QAction("Upload Directory Contents", self)
        uploadDirectoryAction.setStatusTip("Upload Directory Contents")
        uploadDirectoryAction.triggered.connect(self.uploadDirectoryDialog)
        self.addAction(uploadDirectoryAction)

    def _provideMagicLinkAction(self):
        provideMagicLinkAction = QAction("Import Magic Link", self)
        provideMagicLinkAction.triggered.connect(self.invokeMagicLinkDialog)
        self.addAction(provideMagicLinkAction)


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
