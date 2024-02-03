from typing import Optional, Union, TYPE_CHECKING
from qtpy import QtCore, QtGui, QtWidgets

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
            progress = item.progressInterconnect.export_progress[item.export["id"]]
        except KeyError:
            # when we're not actually tracking download progress...
            completed = -1  # minimum - 1 indicates progress hasn't started
            text = item.name
            speed = ""
        else:
            completed = progress.int32_progress()
            text = progress.export_name
            # speed = progress.display_rate

        progressBarOption = QtWidgets.QStyleOptionProgressBar()
        progressBarOption.state = option.state | QtWidgets.QStyle.StateFlag.State_Horizontal
        progressBarOption.palette = option.palette
        progressBarOption.minimum = 0
        progressBarOption.maximum = (2 ** 32 - 1) // 2
        progressBarOption.progress = completed
        progressBarOption.textVisible = True
        progressBarOption.rect = option.rect

        fontMetrics = QtGui.QFontMetrics(option.font)

        # speed_report_rect = fontMetrics.boundingRect(
        #     option.rect,
        #     QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.TextFlag.TextSingleLine,
        #     speed
        # )
        item_name = fontMetrics.elidedText(
            text,
            QtCore.Qt.TextElideMode.ElideMiddle,
            option.rect.width()
            # option.rect.width() - speed_report_rect.width()
        )
        text_name_rect = fontMetrics.boundingRect(
            option.rect,
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.TextFlag.TextSingleLine,
            item_name,
        )
        progressBarOption.fontMetrics = fontMetrics
        painter.save()
        painter.setFont(option.font)
        QtWidgets.QApplication.style().drawControl(
            QtWidgets.QStyle.ControlElement.CE_ProgressBar,
            progressBarOption,
            painter
        )
        painter.drawText(
            text_name_rect,
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.TextFlag.TextSingleLine,
            item_name
        )
        # painter.drawText(
        #     speed_report_rect,
        #     QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.TextFlag.TextSingleLine,
        #     speed
        # )
        painter.restore()
        return None


class ExportItem(QtCore.QObject):

    def __init__(self, export: Export, parent: 'AOIItem', progressInterconnect: 'QtProgress') -> None:
        super().__init__()
        self._parentItem = parent
        self.export = export
        self.name = self.export['name']
        self.export_files = self.export['exportfiles']
        self._data = ["Export"]
        self.progressInterconnect = progressInterconnect

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
        self._data = ["AOI"]
        self.childItems = [ExportItem(export, self, progressInterconnect) for export in aoi['exports']]
        self.progressInterconnect = progressInterconnect

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
        # self.mapFromUrlToIndex: dict[str, QtCore.QModelIndex] = {}

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

    def data(
        self,
        index: QtCore.QModelIndex,
        role=QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Optional[str]:
        if not index.isValid():
            return None

        item: Union[AOIItem, ExportItem] = index.internalPointer()

        if role == QtCore.Qt.ItemDataRole.DisplayRole and index.column() == 0:
            return item.name
        return None

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
        progressInterconnect.taskUpdated.connect(self._updateTask)
        progressInterconnect.taskCompleted.connect(self._updateTask)

    def _updateTask(self, _: 'ProgressTracking'):
        for row in range(self.rowCount()):
            aoi_index = self.index(row, 0)
            n_exports = self.rowCount(parent=aoi_index)
            export_index_top = self.index(0, 0, parent=aoi_index)

            export_index_bottom = self.index(n_exports - 1, 0, parent=aoi_index)
            self.dataChanged.emit(
                export_index_top,
                export_index_bottom,
                [
                    QtCore.Qt.ItemDataRole.DisplayRole,
                    QtCore.Qt.ItemDataRole.UserRole
                ]
            )

    def clear(self) -> None:
         self.beginResetModel()
         self.rootItem = None
         self.endResetModel()
