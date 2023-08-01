from typing import Optional, Union, TYPE_CHECKING
from qtpy import QtCore, QtGui, QtWidgets
import qasync

from doppkit.grid import Export, AOI

if TYPE_CHECKING:
    from .window import QtProgress, ProgressTracking




class ExportDelegate(QtWidgets.QStyledItemDelegate):

    def __int__(self, parent=None):
        super().__init__(parent)

    def paint(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
    ) -> None:

        item: Union['AOIItem', 'ExportItem'] = index.internalPointer()
        if isinstance(item, AOIItem):
            return super().paint(painter, option, index)

        try:
            progress = item.progressInterconnect.tasks[item.export["pk"]]
        except KeyError:
            # when we're not actually tracking download progress...
            completed = 0
        else:
            completed = progress.percentage()
        progressBarOption = QtWidgets.QStyleOptionProgressBar()
        progressBarOption.rect = option.rect
        progressBarOption.state = option.state | QtWidgets.QStyle.StateFlag.State_Horizontal
        progressBarOption.palette = option.palette
        progressBarOption.minimum = 0
        progressBarOption.maximum = item.total
        progressBarOption.progress = completed
        progressBarOption.text = f"{item.name}\t{progressBarOption.maximum}"
        progressBarOption.textVisible = True
        progressBarOption.textAlignment = QtCore.Qt.AlignmentFlag.AlignLeft
        painter.save()
        painter.setFont(QtGui.QFont("Arial", pointSize=10))
        QtWidgets.QApplication.style().drawControl(
            QtWidgets.QStyle.ControlElement.CE_ProgressBar,
            progressBarOption,
            painter
        )
        painter.restore()



class ExportItem(QtCore.QObject):

    def __init__(self, export: Export, parent: 'AOIItem', progressInterconnect: 'QtProgress') -> None:
        super().__init__()
        self._parentItem = parent
        self.export = export
        self.name = self.export['name']
        self.export_files = self.export['exportfiles']
        # self.size = export.get("complete_size", 1)  # complete_size only in newer GRiD API
        self.total = 100
        self.progress = 0
        self._data = ["Export"]
        self.progressInterconnect = progressInterconnect
        self.progressInterconnect.taskUpdated.connect(self.updateProgress)

    def updateProgress(self, progress: 'ProgressTracking'):
        if progress.export_pk == self.export["pk"]:
            self.total = 100
            self.progress = progress.percentage()

    def parentItem(self) -> 'AOIItem':
        return self._parentItem

    @staticmethod
    def childCount():
        return 0

    def data(self, section: int) -> str:
        try:
            return self._data[section]
        except IndexError:
            return ""

class AOIItem:

    def __init__(self, aoi: AOI, parent: 'RootItem', progressInterconnect: 'QtProgress') -> None:
        super().__init__()
        self._parentItem = parent
        self.aoi = aoi
        self.name = aoi['name']
        self.progress = 0
        self._data = ["AOI"]
        self.childItems = [ExportItem(export, self, progressInterconnect) for export in aoi['exports']]
        # self.size = sum(export.size for export in self.childItems)
        self.total = 100
        self.progressInterconnect = progressInterconnect
        # progressInterconnect.taskUpdated.connect(self.updateProgress)

    # @qasync.asyncSlot(object)
    # def updateProgress(self, _: 'ProgressTracking'):
    #     export_progress = self.progressInterconnect.aois[self.aoi["pk"]]
    #     total_size = sum(progress.current for progress in export_progress)
    #     self.progress = total_size
    #     print("AOI Progress Called!")

    def child(self, row: int) -> Optional[ExportItem]:
        try:
            return self.childItems[row]
        except IndexError:
            return None

    def childCount(self) -> int:
        return len(self.childItems)

    @staticmethod
    def row() -> int:
        return 0

    def parentItem(self) -> 'RootItem':
        return self._parentItem

    def data(self, section: int) -> str:
        try:
            return self._data[section]
        except IndexError:
            return ""

    def __repr__(self):
        return f"{self.name=}\t{self.childItems=}"


class RootItem:

    def __init__(self) -> None:
        super().__init__()
        self.childItems: list[AOIItem] = []
        self.name = "root"
        self._data = ["AOI", "Export"]

    def appendChild(self, child: AOIItem) -> None:
        self.childItems.append(child)

    def childCount(self) -> int:
        return len(self.childItems)

    def child(self, row: int) -> Optional[AOIItem]:
        try:
            return self.childItems[row]
        except IndexError:
            return None
    @staticmethod
    def parentItem() -> None:
        return None
    def data(self, section: int) -> str:
        try:
            return self._data[section]
        except IndexError:
            return ""

    @classmethod
    def load(
        cls,
        areas_of_interest: list[AOI],
        progressInterconnect: 'QtProgress'
    ) -> 'RootItem':
        rootItem = RootItem()
        for aoi in areas_of_interest:
            child = AOIItem(aoi, rootItem, progressInterconnect)
            rootItem.appendChild(child)
        return rootItem


class ExportModel(QtCore.QAbstractItemModel):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:

        super().__init__(parent)
        self.rootItem: Optional[AOIItem] = None

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        parentItem = parent.internalPointer() if parent.isValid() else self.rootItem
        childItem = parentItem.child(row)
        if childItem is None:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, childItem)

    def parent(self, index: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem: Union[ExportItem, AOIItem] = index.internalPointer()
        parentItem = childItem.parentItem()
        if parentItem is self.rootItem:
            return QtCore.QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        parentItem = parent.internalPointer() if parent.isValid() else self.rootItem
        return parentItem.childCount()

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 1

    def data(self, index: QtCore.QModelIndex, role=QtCore.Qt.ItemDataRole.DisplayRole) -> Optional[str]:
        if not index.isValid():
            return None

        item: Union[AOIItem, ExportItem] = index.internalPointer()

        if role == QtCore.Qt.ItemDataRole.DisplayRole and index.column() == 0:
            return item.name

        elif role == QtCore.Qt.ItemDataRole.UserRole and index.column() == 1:
            return item.progress

    def headerData(
            self,
            section: int,
            orientation: QtCore.Qt.Orientation,
            role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str:
        if orientation == QtCore.Qt.Orientation.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.rootItem.data(section)
        return ""

    def load(self, data: list[AOI], progressInterconnect: 'QtProgress') -> None:
        self.beginResetModel()
        self.rootItem = RootItem.load(data, progressInterconnect)
        self.endResetModel()

    def clear(self) -> None:
         self.load([])
