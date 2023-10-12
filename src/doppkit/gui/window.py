import os
from .. import __version__
from ..grid import Grid, AOI
from .cache import cache
from qtpy import QtCore, QtGui, QtWidgets
from typing import Optional, NamedTuple
from collections import defaultdict
from dataclasses import dataclass
import pathlib
import logging
import math
import time
from urllib.parse import urlparse

import qasync


from .ExportView import ExportModel, ExportDelegate
from .LogWidget import LoggingDialog
from .MenuBar import MenuBar

logger = logging.getLogger("doppkit")

class ExportFileProgress(NamedTuple):
    url: str
    export_pk: int
    current: int = 0
    total: int = 1
    is_complete: bool = False


class QtProgress(QtCore.QObject):

    taskCompleted = QtCore.Signal(object)
    taskAdded = QtCore.Signal(object)
    taskUpdated = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        # key is the export PK
        self.export_progress: dict[int, ProgressTracking] = {}

        # key is AOI PK
        self.aois: dict[int, list[ProgressTracking]] = defaultdict(list)

        self.urls_to_export_pk: dict[str, int] = {}

        self.export_files: dict[int, dict[str, ExportFileProgress]] = defaultdict(dict)

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

        export_pk = self.urls_to_export_pk[url]
        self.export_files[export_pk][url] = ExportFileProgress(
            url,
            export_pk=export_pk,
            total=total
        )

    def update(self, name: str, url: str, completed: int) -> None:
        export_pk = self.urls_to_export_pk[url]
        old_progress = self.export_files[export_pk][url]
        self.export_files[export_pk][url] = ExportFileProgress(
            url,
            export_pk=export_pk,
            current=completed,
            total=old_progress.total
        )

        export_progress = self.export_progress[export_pk]
        export_progress.update(
            sum(
                file_progress.current
                for file_progress
                in self.export_files[export_pk].values()
            )
        )
        self.taskUpdated.emit(export_progress)

    def complete_task(self, name: str, url: str) -> None:
        export_pk = self.urls_to_export_pk[url]
        old_progress = self.export_files[export_pk][url]
        self.export_files[export_pk][url] = ExportFileProgress(
            url,
            export_pk,
            current=old_progress.total,
            total=old_progress.total,
            is_complete=True
        )

        export_progress = self.export_progress[export_pk]
        export_progress.update(
            sum(
                file_progress.current
                for file_progress
                in self.export_files[export_pk].values()
            )
        )

        if all(export_file.is_complete for export_file in self.export_files[export_pk].values()):
            export_progress.is_complete = True
            self.taskCompleted.emit(export_progress)

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

        # Download Progress Viewer
        self.exportView = None

        # Log Viewer
        self.logView = LoggingDialog()

        self.setMenuBar(MenuBar())

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
        geometry: QtCore.QByteArray = settings.value("geometry", None)
        if geometry is not None:
           self.restoreGeometry(geometry)
        settings.endGroup()

        # read SSL White list settings
        ssl_white_list = settings.value("grid/ssl_url_white_list", None)
        if ssl_white_list is None:
            # setting default URLs to skip
            ssl_white_list = ["https://grid.nga.smil.mil", "https://grid.nga.ic.gov"]
            settings.setValue("grid/ssl_url_white_list", ssl_white_list)

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

        self.progressInterconnect = QtProgress()
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

    def showLogView(self):
        raise self.logView.show()

    def gridURLChanged(self):
        self.doppkit.url = QtCore.QUrl.fromUserInput(self.sender().currentText()).url()
        setting = QtCore.QSettings()
        setting.setValue("grid/url", self.doppkit.url)

    def downloadDirectoryChanged(self):
        self.doppkit.directory = os.fsdecode(self.sender().text())
        setting = QtCore.QSettings()
        setting.setValue("grid/download", self.doppkit.directory)
    
    def aoisChanged(self) -> None:
        try:
            self.AOI_pks = [int(aoi) for aoi in self.sender().text().split(",")]
        except (IndexError, ValueError):
            self.AOI_pks = []

    def tokenChanged(self) -> None:
        self.doppkit.token = self.sender().text().strip()
        setting = QtCore.QSettings()
        setting.setValue("grid/token", self.doppkit.token)

    @qasync.asyncSlot()
    async def listExports(self):
        self.buttonList.setEnabled(False)
        # TODO: this should accept a list of AOIs

        # need to determine if we should skip SSL verification...
        # first, is SSL verification enabled?
        settings = QtCore.QSettings()
        enable_ssl = settings.value("grid/ssl_verification", type=bool)
        # if enabled, check the other elements...
        if enable_ssl:
            # check if the GRiD URL is in the white-list
            whitelisted_urls = settings.value("grid/ssl_url_white_list", [], type=list)
            whitelisted_host_names = {urlparse(url).hostname for url in whitelisted_urls}
            hostname = urlparse(self.doppkit.url).hostname
            if hostname in whitelisted_host_names:
                enable_ssl = False
        enabled = "enabled" if enable_ssl else "disabled"
        logger.debug(f"POSTing to GRiD with SSL {enabled}")
        self.doppkit.disable_ssl_verification = not enable_ssl

        api = Grid(self.doppkit)
        if not self.AOI_pks:
            # there is no AOI entered...
            self.buttonList.setEnabled(True)
            return None
        self.AOIs = await api.get_aois(self.AOI_pks[0])
        model = ExportModel()
        model.clear()

        self.exportView = TreeView()
        self.exportView.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.NoSelection
        )
        self.exportView.setWordWrap(False)
        self.exportView.setTextElideMode(QtCore.Qt.TextElideMode.ElideMiddle)
        self.exportView.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.exportView.setUniformRowHeights(True)

        self.exportView.setModel(model)
        model.load(self.AOIs, self.progressInterconnect)

        # self.exportView.header().setStretchLastSection(True)

        self.exportView.setItemDelegateForColumn(0, ExportDelegate())
        self.exportView.expandAll()
        self.exportView.updateGeometries()

        self.exportView.setAlternatingRowColors(True)
        treeViewSize = self.exportView.size()
        treeViewSize.setWidth(400)
        self.exportView.resize(treeViewSize)

        self.exportView.show()
        self.buttonList.setEnabled(True)


    @qasync.asyncSlot()
    async def downloadExports(self):
        self.buttonDownload.setEnabled(False)
        await self.listExports()  # get the exports

        if not self.AOI_pks:
            # no AOIs entered...
            self.buttonDownload.setEnabled(True)
            return None

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
                        logger.debug(f"File already exists, skipping {filename}")
                    else:
                        urls.append(export_file["url"])
                        self.progressInterconnect.urls_to_export_pk[export_file["url"]] = export["pk"]
                progress_tracker = ProgressTracking(
                    export["pk"],
                    export_name=export["name"],
                    aoi_pk=aoi["pk"],
                    aoi_name=aoi["name"],
                    current=0,
                    total=export["complete_size"],
                )
                self.progressInterconnect.export_progress[export["pk"]] = progress_tracker
                self.progressInterconnect.aois[aoi["pk"]].append(progress_tracker)

        _ = await cache(self.doppkit, urls, {}, progress=self.progressInterconnect)
        self.buttonDownload.setEnabled(True)

@dataclass
class ProgressTracking:
    export_pk: int
    export_name: str
    aoi_pk: int
    aoi_name: str
    current: int
    total: int
    elapsed: float = time.perf_counter()
    rate: float = 0.0
    is_complete: bool = False
    rate_update_timer = time.perf_counter()
    display_rate: str = "0.0 B/s"

    def ratio(self) -> float:
        return self.current / self.total

    def percentage(self) -> int:
        return math.floor(100 * self.ratio())

    def int32_progress(self):
        return math.floor(((2 ** 32 - 1) // 2) * self.ratio())

    def update(self, current: int) -> None:
        old_current = self.current
        self.current = current
        diff = current - old_current
        now = time.perf_counter()
        duration = now - self.elapsed
        self.rate = diff / duration
        if now - self.rate_update_timer > 1.0:
            self.update_download_rate()
            self.rate_update_timer = now
        self.elapsed = now

    def update_download_rate(self):
        if self.is_complete:
            self.display_rate = "Complete"
            return None

        for exponent, prefix in zip((6, 3, 0), ("M", "k", "")):
            multiple = 10 ** exponent
            if self.rate > multiple:
                self.display_rate = f"{(self.rate / multiple):.1f} {prefix}B/s"
                break
        else:
            self.display_rate = "0.0 B/s"
        return None

    def __str__(self):
        return f"{self.export_name} - ({self.display_rate})"
