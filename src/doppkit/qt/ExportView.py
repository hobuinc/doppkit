from typing import Optional, Union
from qtpy import QtCore, QtWidgets


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


    def index(self, row: int, column: int, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
        parentItem = parent.internalPointer() if parent.isValid() else self.rootItem
        childItem = parentItem.child(row)
        if childItem is None:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, childItem)

    def parent(self, index: QtCore.QModelIndex = QtCore.QModelIndex()) -> QtCore.QModelIndex:
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
        parentItem = parent.internalPointer() if parent.isValid() else self.rootItem
        return parentItem.childCount()


    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 1

    def data(self, index: QtCore.QModelIndex, role=QtCore.Qt.ItemDataRole.DisplayRole) -> Optional[str]:
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == QtCore.Qt.ItemDataRole.DisplayRole and index.column() == 0:
            return item.name

    def headerData(
            self,
            section: int,
            orientation: QtCore.Qt.Orientation,
            role: QtCore.Qt.ItemDataRole = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> str:
        if orientation == QtCore.Qt.Orientation.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return self.rootItem.data(section)
        return ""

    def load(self, data: dict[str, list[str]]) -> None:
        self.beginResetModel()
        self.rootItem = AOIItem.load(data)
        self.endResetModel()

    def clear(self) -> None:
         self.load({})
