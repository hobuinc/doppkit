from typing import Optional, Union
from qtpy import QtCore

from doppkit.grid import Export, AOI



class ExportItem:

    def __init__(self, export: Export, parent: 'AOIItem') -> None:
        super().__init__()
        self._parentItem = parent
        self.export = export
        self.name = self.export['name']
        self.export_files = self.export['exportfiles']
        self._data = ["Export"]

    def parentItem(self):
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

    def __init__(self, aoi: AOI, parent: 'RootItem') -> None:
        super().__init__()
        self._parentItem = parent
        self.childItems = [ExportItem(export, self) for export in aoi['exports']]
        self.aoi = aoi
        self.name = aoi['name']
        self._data = ["AOI"]

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
    ) -> 'RootItem':
        rootItem = RootItem()
        for aoi in areas_of_interest:
            child = AOIItem(aoi, rootItem)
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

    def load(self, data: list[AOI]) -> None:
        self.beginResetModel()
        self.rootItem = RootItem.load(data)
        self.endResetModel()

    def clear(self) -> None:
         self.load([])
