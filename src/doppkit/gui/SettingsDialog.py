from enum import IntEnum
import logging
import os

from typing import Optional, TYPE_CHECKING
from qtpy.QtGui import QAbstractFileIconProvider, QValidator
from qtpy.QtWidgets import QDialog, QFileDialog, QGroupBox, QLineEdit, QHBoxLayout, QVBoxLayout, QLabel, QWidget, QRadioButton, QListWidget, QFileIconProvider, QTabWidget, QDialogButtonBox, QPushButton, QListWidgetItem
from qtpy.QtCore import QObject, Slot, Qt, QSettings, QStandardPaths, QUrl

if TYPE_CHECKING:
    from .window import Window

logger = logging.getLogger(__name__)

class TabEnum(IntEnum):
    sslSettings = 0
    # add other settings tabs here...


class SSLDirectoryValidator(QValidator):

    def validate(self, input_: str, pos: int) -> tuple[QValidator.State, str, int]:
        if os.path.isdir(input_) and os.access(input_, os.R_OK):
            state = QValidator.State.Acceptable
        else:
            state = QValidator.State.Intermediate
        return state, input_, pos


class SSLFileValidator(QValidator):

    def validate(self, input_: str, pos: int) -> tuple[QValidator.State, str, int]:
        if os.path.isfile(input_) and os.access(input_, os.R_OK):
            state = QValidator.State.Acceptable
        else:
            state = QValidator.State.Intermediate
        return state, input_, pos

class URLValidator(QValidator):

    def validate(self, input_: str, pos: int) -> tuple[QValidator.State, str, int]:
        url = QUrl.fromUserInput(input_)
        if url.isValid():
            state = QValidator.State.Acceptable
        else:
            state = QValidator.State.Intermediate
        return state, input_, pos



class SettingsTabContents(QWidget):
    def __init__(self, parent: QTabWidget) -> None:
        super().__init__(parent)
        self.settingsDialog = self.parent().parent()
        standardLayout = QVBoxLayout(self)

        self.settingsContentLayout = QVBoxLayout() 
        standardLayout.addLayout(self.settingsContentLayout)
        standardLayout.addStretch()

        self._insertLastRow()
        self.setLayout(standardLayout)
    
    def _insertLastRow(self):
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok,
            Qt.Orientation.Horizontal,
            parent=self
        )
        box.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self.settingsDialog.close)
        self.layout().addWidget(box)


class SSLSettings(SettingsTabContents):

    def __init__(self, parent: 'SettingsDialog') -> None:
        super().__init__(parent)
        settings = QSettings()

        name = "SSL Settings"
        self.setAccessibleName(name)
        self.parent().insertTab(TabEnum.sslSettings, self, name)

        # Enable/Disable
        sslToggleLayout = QVBoxLayout()
        sslStatusGroupBox = QGroupBox("SSL Verification")
        enabledRadio = QRadioButton("Enabled")
        disabledRadio = QRadioButton("Disabled")
        # don't need to connect the disabled button ...
        if settings.value("grid/ssl_verification", type=bool):
            logger.debug("SSL verification is set to enabled")
            enabledRadio.setChecked(True)
        else:
            logger.debug("SSL verification is set to disabled")
            disabledRadio.setChecked(True)

        enabledRadio.toggled.connect(self.enableSSL)

        sslToggleLayout.addWidget(enabledRadio)
        sslToggleLayout.addWidget(disabledRadio)
        sslToggleLayout.addStretch(1)
        sslStatusGroupBox.setLayout(sslToggleLayout)

        # Preset URLs
        presetUrlsLayout = QVBoxLayout()
        presetUrlsLabel = QLabel("GRiD Servers To Disable SSL Verification")
        labelFont = presetUrlsLabel.font()
        labelFont.setPointSize(10)
        presetUrlsLabel.setFont(labelFont)

        self.listWidget = QListWidget()
        presetUrlsLabel.setBuddy(self.listWidget)
        white_list_urls = settings.value("grid/ssl_url_white_list", None)

        if white_list_urls is not None:
            for url in white_list_urls:
                self.listWidget.addItem(url)
        
        self.listWidget.itemChanged.connect(self.onItemChanged)
        addUrlButton = QPushButton("+")
        delUrlButton = QPushButton("-")
        delUrlButton.clicked.connect(self.removeSSLWhiteListUrl)
        addUrlButton.clicked.connect(self.addSSLWhiteListUrl)
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(addUrlButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(delUrlButton)

        presetUrlsLayout.addWidget(presetUrlsLabel)
        presetUrlsLayout.addWidget(self.listWidget)
        presetUrlsLayout.addLayout(buttonLayout)
        
        # specify SSL certificates
        sslDirectoryLabel = QLabel("Directory of SSL Certificates")
        sslDirectoryLabel.setFont(labelFont)
        sslDirectoryEdit = QLineEdit()
        sslDirectoryValidator = SSLDirectoryValidator(parent=None)
        sslDirectoryEdit.setValidator(sslDirectoryValidator)
        sslDirectoryLabel.setBuddy(sslDirectoryEdit)
        sslDirectoryEdit.setText(
            str(
                settings.value(
                    "grid/ssl_cert_dir",
                    os.getenv("SSL_CERT_DIR", "")
                )
            )
        )
        sslDirectoryEdit.editingFinished.connect(self.sslDirectoryChanged)

        icons = QFileIconProvider()
        directoryIcon = icons.icon(QAbstractFileIconProvider.IconType.Folder)
        sslDirectoryAction = sslDirectoryEdit.addAction(
            directoryIcon,
            QLineEdit.ActionPosition.LeadingPosition
        )
        sslDirectoryAction.triggered.connect(self.showSSLDirectoryDialog)
        sslFileLabel = QLabel("SSL Certificate")
        sslFileLabel.setFont(labelFont)
        sslFileEdit = QLineEdit()
        sslFileValidator = SSLFileValidator(parent=None)
        sslFileEdit.setValidator(sslFileValidator)
        sslFileLabel.setBuddy(sslFileEdit)
        sslFileEdit.setText(
            str(
                settings.value(
                    "grid/ssl_cert_file",
                    os.getenv("SSL_CERT_FILE", "")
                )
            )
        )
        sslFileEdit.editingFinished.connect(self.sslFileChanged)
        fileIcon = icons.icon(QAbstractFileIconProvider.IconType.File)
        sslFileAction = sslFileEdit.addAction(
            fileIcon,
            QLineEdit.ActionPosition.LeadingPosition
        )
        sslFileAction.triggered.connect(self.showSSLFileDialog)

        sslFilesLayout = QVBoxLayout()
        sslFilesLayout.addWidget(sslDirectoryLabel)
        sslFilesLayout.addWidget(sslDirectoryEdit)
        sslFilesLayout.addWidget(sslFileLabel)
        sslFilesLayout.addWidget(sslFileEdit)
        sslFilesLayout.addStretch(1)

        enabledOptionsLayout = QHBoxLayout()
        enabledOptionsLayout.addLayout(presetUrlsLayout)
        enabledOptionsLayout.addLayout(sslFilesLayout)

        self.settingsContentLayout.addWidget(sslStatusGroupBox)
        self.settingsContentLayout.addLayout(enabledOptionsLayout)

    @Slot()
    def removeSSLWhiteListUrl(self):
        rows_to_remove = {
            self.listWidget.row(item) for item in self.listWidget.selectedItems()
        }
        for row in sorted(rows_to_remove, reverse=True):
            self.listWidget.takeItem(row)

        self._updateSSLWhiteListUrls()


    @Slot()
    def addSSLWhiteListUrl(self):
        new_item = QListWidgetItem("")
        new_item.setFlags(new_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.listWidget.insertItem(self.listWidget.count(), new_item)
        self.listWidget.editItem(new_item)

    @Slot(QListWidgetItem)
    def onItemChanged(self, item: QListWidgetItem):
        # likely inefficient but if it's stupid and it works...
        self._updateSSLWhiteListUrls()

    def _updateSSLWhiteListUrls(self):
        urls = [
            self.listWidget.item(row).text()
            for row in range(self.listWidget.count())
        ]
        settings = QSettings()
        settings.setValue("grid/ssl_url_white_list", urls)

    @Slot()
    def sslDirectoryChanged(self):
        directory = os.fsdecode(self.sender().text())
        if os.path.isdir(directory):
            os.environ["SSL_CERT_DIR"] = directory
            settings = QSettings()
            settings.setValue("grid/ssl_cert_dir", directory)
            logger.debug(f"Setting variable SSL_CERT_DIR to {directory}")
        else:
            if "SSL_CERT_DIR" in os.environ:
                del os.environ["SSL_CERT_DIR"]
            logger.warning(f"Did not set SSL_CERT_DIR to {directory} as it is not a directory")
        return None

    @Slot()
    def sslFileChanged(self):
        cert_file = os.fsdecode(self.sender().text())
        if os.path.isfile(cert_file):
            os.environ["SSL_CERT_FILE"] = cert_file
            logger.debug("SSL_CERT_FILE set")
        else:
            logger.warning("SSL_CERT_FILE was not set due to entry not being a file")
        return None

    @Slot()
    def showSSLDirectoryDialog(self):
        settings = QSettings()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select SSL Certificate Directory",
            str(
                settings.value(
                    "grid/ssl_cert_dir",
                    QStandardPaths.standardLocations(
                        QStandardPaths.StandardLocation.HomeLocation
                    )[0]
                )
            ),
            QFileDialog.Option.ShowDirsOnly
        )
        if directory == "":
            # dialog was cancelled
            return None

        sslDirectoryEdit = self.sender().parent()
        sslDirectoryEdit.setText(directory)
    
    @Slot()
    def showSSLFileDialog(self):
        settings = QSettings()
        filepath = QFileDialog.getOpenFileName(
            self,
            "Select SSL Certificate",
            str(
                settings.value(
                    "grid/ssl_cert_file",
                    QStandardPaths.standardLocations(
                        QStandardPaths.StandardLocation.HomeLocation
                    )[0]
                )
            ),
        )
        if filepath == "":
            # dialog was cancelled
            return None
        
        sslFileEdit = self.sender().parent()
        sslFileEdit.setText(filepath)

    @Slot(bool)
    def enableSSL(self, checked: bool):
        logger.info(f"Toggling Verify SSL to {checked}")
        otherLayout = self.settingsContentLayout.itemAt(1)
        if otherLayout is None:
            # layout isn't finished populating
            return None
        for item in self.children():
            if isinstance(item, (QListWidget, QLineEdit, QPushButton)):
                item.setEnabled(checked)
        settings = QSettings()
        settings.setValue("grid/ssl_verification", checked)


class SettingsDialog(QDialog):

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.tabWidget = QTabWidget(self)
        self.sslTab = SSLSettings(self.tabWidget)
        layout = QVBoxLayout()
        layout.addWidget(self.tabWidget)
        self.setLayout(layout)
