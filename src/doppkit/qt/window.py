import os
from doppkit import __version__
from doppkit.grid import Api
from qtpy import QtCore, QtGui, QtWidgets
from typing import Optional, Union


class DirectoryValidator(QtGui.QValidator):

    def validate(self, input_: str, pos: int) -> tuple[QtGui.QValidator.State, str, int]:
        if os.path.isdir(input_) and os.access(input_, os.W_OK):
            state = QtGui.QValidator.State.Acceptable
        else:
            state = QtGui.QValidator.State.Intermediate
        return (state, input_, pos)
    
class URLValidator(QtGui.QValidator):

    def validate(self, input_: str, pos: int) -> tuple[QtGui.QValidator.State, str, int]:
        # url = QtCore.QUrl(input_)
        url = QtCore.QUrl.fromUserInput(input_)
        if url.isValid():
            state = QtGui.QValidator.State.Acceptable
        else:
            state = QtGui.QValidator.State.Intermediate
        return (state, input_, pos)



    

class TreeView(QtWidgets.QTreeView):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        return None


class AOIItem:

    def __init__(self, parent: Optional['AOIItem'] = None, name: str = "") -> None:
        super().__init__()
        self._parentItem: Optional['AOIItem'] = parent
        self.childItems: list['AOIItem'] = []    
        self.name = name

    def appendChild(self, item: 'AOIItem') -> None:
        self.childItems.append(item)
    
    def child(self, row: int) -> Optional['AOIItem']:
        try:
            return self.childItems[row]
        except IndexError:
            return None

    def childCount(self) -> int:
        return len(self.childItems)

    def row(self) -> int:
        return 0 if self.parentItem() is None else self.parentItem().childItems.index(self)
    
    def parentItem(self) -> Optional['AOIItem']:
        return self._parentItem
    
    def __repr__(self):
        return f"{self.name=}\t{self.childItems=}"

    @classmethod
    def load(
        cls,
        value: Union[list[str], dict[str, list[str]], str],
        parent: Optional['AOIItem'] = None
    ) -> 'AOIItem':
        rootItem = AOIItem(parent)
        rootItem.name = "root"
        if isinstance(value, dict):    
            for aoi_name, exports in value.items():
                child = cls.load(exports, rootItem)
                child.name = aoi_name
                rootItem.appendChild(child)
        elif isinstance(value, list):
            for export in value:
                child = cls.load(export, rootItem)
                child.name = export
                rootItem.appendChild(child)
        else:
            rootItem.name = value
        return rootItem


class ExportModel(QtCore.QAbstractItemModel):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:

        super().__init__(parent)
        self.rootItem = AOIItem()

        return None

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
        
        childItem = parentItem.child(row)
        if childItem is None:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, childItem)

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()
        
        childItem = index.internalPointer()
        parentItem = childItem.parentItem()
        if parentItem == self.rootItem:
            return QtCore.QModelIndex()
        
        return self.createIndex(parentItem.row(), 0, parentItem)
    
    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
        
        return parentItem.childCount()
        

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 1

    def data(self, index: QtCore.QModelIndex, role=QtCore.Qt.ItemDataRole.DisplayRole) -> Optional[str]:
        if not index.isValid():
            print("Got invalid index, returning None")
            return None

        item = index.internalPointer()

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return item.name

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: QtCore.Qt.ItemDataRole) -> str:
        if orientation == QtCore.Qt.Orientation.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.rootItem.data(section)
        return ""

    def load(self, data: dict[str, list[str]]) -> None:
        self.beginResetModel()
        self.rootItem = AOIItem.load(data)
        self.endResetModel()            
    
    def clear(self) -> None:
         self.load({})


# class ExportWindow(QtWidgets.QWidget):

#     def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
#         super().__init__(parent)
#         self.view = QtWidgets.QTreeView(self)
#         self.view.setAlternatingRowColors(True)
#         # self.setCentralWidget(self.view)

#         self.model = ExportModel()
#         self.view.setModel(self.model)
#         self.view.expandAll()
#         return None
        



class Window(QtWidgets.QMainWindow):

    def __init__(self, doppkit_application, *args):
        super().__init__(*args)

        self.setGeometry(300, 300, 300, 220)
        self.setWindowTitle(f"doppkit - {__version__}")
        self.doppkit = doppkit_application
        self.AOIs: list[int] = []

        self.exportView = TreeView()
        self.exportView.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.exportView.header().setCascadingSectionResizes(True)
        self.exportView.setHeaderHidden(False)
        contents = QtWidgets.QWidget()
        self.setCentralWidget(contents)

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
        urlValidator = URLValidator()
        urlLineComboBox.setValidator(urlValidator)

        # Token Widgets
        tokenLabel = QtWidgets.QLabel("&Token")
        tokenLabel.setFont(labelFont)
        tokenLineEdit = QtWidgets.QLineEdit()
        tokenLineEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.PasswordEchoOnEdit)
        tokenLabel.setBuddy(tokenLineEdit)

        # AOI Widgets
        aoiLabel = QtWidgets.QLabel("&AOI")
        aoiLabel.setFont(labelFont)
        aoiLineEdit = QtWidgets.QLineEdit()

        # TODO: don't use IntValidator, should accept coma separated values
        aoiValidator = QtGui.QIntValidator()
        aoiValidator.setBottom(0)
        aoiLineEdit.setValidator(aoiValidator)
        aoiLineEdit.editingFinished.connect(self.aoisChanged)
        aoiLabel.setBuddy(aoiLineEdit)

        # Download Location
        downloadLabel = QtWidgets.QLabel("&Download Location")
        downloadLabel.setFont(labelFont)
        downloadLineEdit = QtWidgets.QLineEdit(
            QtCore.QStandardPaths.standardLocations(
                QtCore.QStandardPaths.StandardLocation.DownloadLocation
            )[0]
        )
        downloadLabel.setBuddy(downloadLineEdit)
        downloadLineEdit.setValidator(DirectoryValidator())
        downloadLineEdit.editingFinished.connect(self.downloadDirectoryChagned)

        icons = QtWidgets.QFileIconProvider()
        downloadIcon = icons.icon(QtGui.QAbstractFileIconProvider.IconType.Folder)
        downloadAction = downloadLineEdit.addAction(
            downloadIcon,
            QtWidgets.QLineEdit.ActionPosition.LeadingPosition
        )

        downloadAction.triggered.connect(self.showDownloadDialog)

        buttonList = QtWidgets.QPushButton("List Exports")
        buttonList.clicked.connect(aoiLineEdit.editingFinished)
        # we connect using a queued connection to ensure that the AOILineEdit
        # registers the finished signal
        buttonList.clicked.connect(
            self.listAOIs,
            QtCore.Qt.ConnectionType.QueuedConnection
        )
        buttonDownload = QtWidgets.QPushButton("Download Exports")

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
        buttonLayout.addWidget(buttonList)
        buttonLayout.addWidget(buttonDownload)

        for widgets in grouping.values():
            for widget in widgets:
                layout.addWidget(widget)

        layout.addLayout(buttonLayout)

        self.show()
    

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
        # TODO: store value on disk
    
    def downloadDirectoryChagned(self):
        self.doppkit.directory = os.fsdecode(self.sender().text())
    
    def aoisChanged(self) -> None:
        self.AOIs = [int(aoi) for aoi in self.sender().text().split(",")]
    
    def listAOIs(self) -> None:
        api = Api(self.doppkit)
        if not self.AOIs:
            # we haven't entered an AOI here yet!
            return None
        self.sender().setEnabled(False)
        try:
            print("Querying GRiD...")
            aois = api.get_aois(self.AOIs[0])
        finally:
            print("Query Finished")
            self.sender().setEnabled(True)
        displayData = {aoi["name"]: [export["name"] for export in aoi["exports"]] for aoi in aois}

        model = ExportModel()
        self.exportView.setModel(model)
        model.load(displayData)
        self.exportView.expandAll()
        self.exportView.resizeColumnToContents(0)
        self.exportView.show()
        self.exportView.setAlternatingRowColors(True)
