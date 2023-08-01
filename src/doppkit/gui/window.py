import os
from .. import __version__
from ..grid import Grid, AOI, Exportfile, Export
from .cache import cache
from qtpy import QtCore, QtGui, QtWidgets
from typing import Optional, TypedDict, NamedTuple
from collections import defaultdict
from dataclasses import dataclass
import pathlib
import logging
import math
import warnings
import qasync


from .ExportView import ExportModel, ExportDelegate


class QtProgress(QtCore.QObject):

    taskRemoved = QtCore.Signal(object)
    taskAdded = QtCore.Signal(object)
    taskUpdated = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        # key is the export PK
        self.tasks: dict[int, ProgressTracking] = {}

        # key is AOI PK
        self.aois: dict[int, list[ProgressTracking]] = defaultdict(list)

        # dictionary of name with URL
        self.urls_to_export_pk: dict[str, int] = {}

    def create_task(self, name: str, url: str, total: int):
        """
        Method adds a task to track the download progress

        Parameters
        ----------
        name
            The name of the file being downloaded
        url
            The URL to contents of the file are being downloaded from
        total
            The total size of the file in bytes

        Returns
        -------
            None
        """

        try:
            export_pk = self.urls_to_export_pk[url]
        except KeyError as e:
            raise RuntimeError("Unexpected URL for tracking download progress received") from e
        else:
            task = self.tasks[export_pk]
            self.taskAdded.emit(task)

    def update(self, name: str, url: str, completed: int) -> None:
        try:
            export_pk = self.urls_to_export_pk[url]
        except KeyError as e:
            raise RuntimeError("Unexpected URL for tracking download progress received") from e
        else:
            task = self.tasks[export_pk]
            task.current = completed
            self.taskUpdated.emit(task)

    def complete_task(self, name: str, url: str) -> None:
        try:
            export_pk = self.urls_to_export_pk[url]
        except KeyError as e:
            raise RuntimeError("Unexpected URL for tracking download progress received") from e
        else:
            task = self.tasks[export_pk]
            task.current = task.total

        # task = self.tasks.pop(export_pk)
        # self.taskRemoved.emit(task)


    def update_export_progress(self):
        pass

    def update_aoi_progress(self):
        pass



class DirectoryValidator(QtGui.QValidator):

    def validate(self, input_: str, pos: int) -> tuple[QtGui.QValidator.State, str, int]:
        if os.path.isdir(input_) and os.access(input_, os.W_OK):
            state = QtGui.QValidator.State.Acceptable
        else:
            state = QtGui.QValidator.State.Intermediate
        return state, input_, pos
    
class URLValidator(QtGui.QValidator):

    def validate(self, input_: str, pos: int) -> tuple[QtGui.QValidator.State, str, int]:
        # url = QtCore.QUrl(input_)
        url = QtCore.QUrl.fromUserInput(input_)
        if url.isValid():
            state = QtGui.QValidator.State.Acceptable
        else:
            state = QtGui.QValidator.State.Intermediate
        return state, input_, pos


class TreeView(QtWidgets.QTreeView):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)


class Window(QtWidgets.QMainWindow):

    def __init__(self, doppkit_application, *args):
        super().__init__(*args)

        self.setGeometry(300, 300, 300, 220)
        self.setWindowTitle(f"doppkit - {__version__}")
        self.doppkit = doppkit_application
        self.AOI_pks: list[int] = []
        self.AOIs: list[AOI] = []  # populated from GRiD

        self.progressTracker = QtProgress()

        self.exportView = TreeView()
        self.exportView.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.exportView.header().setCascadingSectionResizes(True)
        self.exportView.setHeaderHidden(False)
        self.exportView.setItemDelegateForColumn(1, ExportDelegate())
        contents = QtWidgets.QWidget()
        self.setCentralWidget(contents)

        settings = QtCore.QSettings()

        layout = QtWidgets.QVBoxLayout(contents)

        # URL Widgets
        urlLabel = QtWidgets.QLabel("&Server")
        labelFont = urlLabel.font()
        labelFont.setPointSize(10)
        urlLineComboBox = QtWidgets.QComboBox()
        urlLineComboBox.addItems(
            [
                "https://grid.nga.mil/grid",
                "https://grid.nga.smil.mil",
                "https://grid.nga.ic.gov"
            ]
        )
        urlLineComboBox.setEditable(True)
        urlLineComboBox.currentTextChanged.connect(self.gridURLChanged)
        urlLabel.setFont(labelFont)
        urlLabel.setBuddy(urlLineComboBox)
        urlValidator = URLValidator(parent=None)
        urlLineComboBox.setValidator(urlValidator)

        # Token Widgets
        tokenLabel = QtWidgets.QLabel("&Token")
        tokenLabel.setFont(labelFont)
        tokenLineEdit = QtWidgets.QLineEdit()
        tokenLineEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.PasswordEchoOnEdit)
        tokenLineEdit.editingFinished.connect(self.tokenChanged)
        tokenLabel.setBuddy(tokenLineEdit)

        # AOI Widgets
        aoiLabel = QtWidgets.QLabel("&AOI")
        aoiLabel.setFont(labelFont)
        aoiLineEdit = QtWidgets.QLineEdit()

        # TODO: don't use IntValidator, should accept coma separated values
        aoiValidator = QtGui.QIntValidator(parent=None, bottom=0)
        aoiValidator.setBottom(0)
        aoiLineEdit.setValidator(aoiValidator)
        aoiLineEdit.editingFinished.connect(self.aoisChanged)
        aoiLabel.setBuddy(aoiLineEdit)

        # Download Location
        downloadLabel = QtWidgets.QLabel("&Download Location")
        downloadLabel.setFont(labelFont)
        downloadLineEdit = QtWidgets.QLineEdit()
        downloadLabel.setBuddy(downloadLineEdit)
        downloadLineEdit.setValidator(DirectoryValidator(parent=None))
        downloadLineEdit.editingFinished.connect(self.downloadDirectoryChanged)

        icons = QtWidgets.QFileIconProvider()
        downloadIcon = icons.icon(QtGui.QAbstractFileIconProvider.IconType.Folder)
        downloadAction = downloadLineEdit.addAction(
            downloadIcon,
            QtWidgets.QLineEdit.ActionPosition.LeadingPosition
        )

        downloadAction.triggered.connect(self.showDownloadDialog)

        self.buttonList = QtWidgets.QPushButton("List Exports")
        self.buttonList.clicked.connect(aoiLineEdit.editingFinished)
        self.buttonList.clicked.connect(tokenLineEdit.editingFinished)
        # we connect using a queued connection to ensure that the AOILineEdit
        # registers the finished signal
        self.buttonList.clicked.connect(
            self.listExports,
            QtCore.Qt.ConnectionType.QueuedConnection
        )
        self.buttonDownload = QtWidgets.QPushButton("Download Exports")
        self.buttonDownload.clicked.connect(aoiLineEdit.editingFinished)
        self.buttonDownload.clicked.connect(tokenLineEdit.editingFinished)
        self.buttonDownload.clicked.connect(downloadLineEdit.editingFinished)
        self.buttonDownload.clicked.connect(
            self.downloadExports,
            QtCore.Qt.ConnectionType.QueuedConnection
        )
        grouping = {
            "aoi": (
                aoiLabel,
                aoiLineEdit
            ),
            "token": (
                tokenLabel,
                tokenLineEdit
            ),
            "destination": (
                downloadLabel,
                downloadLineEdit
            ),
            "url": (
                urlLabel,
                urlLineComboBox
            ),
        }

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(self.buttonList)
        buttonLayout.addWidget(self.buttonDownload)

        for widgets in grouping.values():
            for widget in widgets:
                layout.addWidget(widget)

        layout.addLayout(buttonLayout)

        # read window settings
        settings.beginGroup("MainWindow")
        geometry = settings.value("geometry", None)
        if geometry is not None:
           self.restoreGeometry(geometry)
        settings.endGroup()

        # populate fields with previously stored values or defaults otherwise
        tokenLineEdit.setText(settings.value("grid/token"))

        urlLineComboBox.setEditText(str(settings.value("grid/url", "https://grid.nga.mil/grid")))
        
        downloadLineEdit.setText(
            str(
                settings.value(
                    "grid/download",
                    QtCore.QStandardPaths.standardLocations(
                        QtCore.QStandardPaths.StandardLocation.DownloadLocation
                    )[0]
                )
            )
        )
        self.show()
    

    def closeEvent(self, evt: QtGui.QCloseEvent) -> None:
        settings = QtCore.QSettings()
        settings.beginGroup("MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.endGroup()

    def showDownloadDialog(self, checked:bool = False):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Open Directory",
            self.doppkit.directory,
            QtWidgets.QFileDialog.Option.ShowDirsOnly
        )

        if directory == "":
            # dialog was cancelled
            return None
        
        lineEdit = self.sender().parent()
        lineEdit.setText(directory)

    def gridURLChanged(self):
        self.doppkit.url = QtCore.QUrl.fromUserInput(self.sender().currentText()).url()
        setting = QtCore.QSettings()
        setting.setValue("grid/url", self.doppkit.url)

    def downloadDirectoryChanged(self):
        self.doppkit.directory = os.fsdecode(self.sender().text())
        setting = QtCore.QSettings()
        setting.setValue("grid/download", self.doppkit.directory)
    
    def aoisChanged(self) -> None:
        self.AOI_pks = [int(aoi) for aoi in self.sender().text().split(",")]

    def tokenChanged(self) -> None:
        self.doppkit.token = self.sender().text().strip()
        setting = QtCore.QSettings()
        setting.setValue("grid/token", self.doppkit.token)

    @qasync.asyncSlot()
    async def listExports(self):
        self.buttonList.setEnabled(False)
        # TODO: this should accept a list of AOIs
        # get AOI objects from GRiD
        api = Grid(self.doppkit)
        self.AOIs = await api.get_aois(self.AOI_pks[0])
        model = ExportModel()
        self.exportView.setModel(model)
        self.progressInterconnect = QtProgress()
        model.load(self.AOIs, self.progressInterconnect)
        self.exportView.setItemDelegateForColumn(0, ExportDelegate())
        self.exportView.expandAll()
        self.exportView.show()
        self.exportView.resizeColumnToContents(0)
        # self.exportView.resizeColumnToContents(1)
        self.exportView.setAlternatingRowColors(True)
        self.buttonList.setEnabled(True)

    @qasync.asyncSlot()
    async def downloadExports(self):
        self.buttonDownload.setEnabled(False)
        await self.listExports()  # get the exports

        api = Grid(self.doppkit)
        # now we get information to each exportfile

        download_dir = pathlib.Path(self.doppkit.directory)
        download_dir.mkdir(exist_ok=True)

        urls = []
        for aoi in self.AOIs:
            for export in aoi["exports"]:
                # need to check for export_files, if not present, we need to populate
                if isinstance(export["exportfiles"], bool):
                    # we need to grab the list of exportfiles...
                    export["exportfiles"] = await api.get_exports(export["pk"])

                # if using the older API, fill in the respective field
                if "export_total_size" not in export.keys():
                    export["export_total_size"] = sum(export_file["filesize"] for export_file in export["exportfiles"])

                if "complete_size" not in export.keys():
                    # auxfile total size attribute not at all accessible in v3 of GRiD API
                    export["complete_size"] = export["export_total_size"] + export.get("auxfile_total_size", 0)

                download_size = 0
                for export_file in export["exportfiles"]:
                    filename = export_file["name"]
                    download_destination = download_dir.joinpath(filename)
                    download_size += export_file["filesize"]
                    # TODO: compare filesizes, not just if it exists
                    if not self.doppkit.override and download_destination.exists():
                        logging.debug(f"File already exists, skipping {filename}")
                    else:
                        urls.append(export_file["url"])
                        self.progressInterconnect.urls_to_export_pk[export_file["url"]] = export["pk"]
                progress_tracker = ProgressTracking(
                    export["pk"],
                    aoi_pk=aoi["pk"],
                    current=0,
                    total=export["complete_size"],
                )
                self.progressInterconnect.tasks[export["pk"]] = progress_tracker
                self.progressInterconnect.aois[aoi["pk"]].append(progress_tracker)

        _ = await cache(self.doppkit, urls, {}, progress=self.progressInterconnect)
        self.buttonDownload.setEnabled(True)

@dataclass
class ProgressTracking:
    export_pk: int
    aoi_pk: int
    current: int
    total: int

    def ratio(self) -> float:
        return self.current / self.total

    def percentage(self) -> int:
        return math.floor(100 * self.ratio())