from typing import TYPE_CHECKING, Optional
import os
from qtpy import QtCore, QtWidgets, QtGui


if TYPE_CHECKING:
    from .window import QtUploadProgress, UploadProgressTracking


class UploadItem(QtCore.QObject):

    def __init__(self, filepath: str, progressInterconnect: 'QtUploadProgress') -> None:
        super().__init__()
        self.filepath = filepath
        self.progressInterconnect = progressInterconnect

class UploadDelegate(QtWidgets.QStyledItemDelegate):

    def __int__(self, parent=None):
        super().__init__(parent)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex
    ) -> None:
        item = index.model().uploads[index.row()]
        text = os.path.basename(item.filepath)

        try:
            progress = item.progressInterconnect.upload_progress[item.filepath]
        except KeyError:
            # when we're not actually tracking download progress...
            completed = -1  # minimum - 1 indicates progress hasn't started
            speed = ""
        else:
            completed = progress.int32_progress()
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




class UploadModel(QtCore.QAbstractListModel):

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.uploads: list[UploadItem] = []


    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        return len(self.uploads)


    def data(
        self,
        index: QtCore.QModelIndex,
        role=QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Optional[str]:
        if not index.isValid():
            return None     

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            row: int = index.row()  # doing this way to make type-hinting happy
            item: UploadItem = self.uploads[row]
            return os.path.basename(item.filepath)
        return None

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.DisplayRole
    ) -> str:
        if orientation == QtCore.Qt.Orientation.Horizontal and role == QtCore.Qt.ItemDataRole:
            return "Upload"
        return ""


    def load(self, data: list[UploadItem], progressInterconnect: 'QtUploadProgress') -> None:
        self.beginResetModel()
        self.uploads = data
        self.endResetModel()
        progressInterconnect.taskUpdated.connect(self._updateTask)
        progressInterconnect.taskCompleted.connect(self._updateTask)


    def _updateTask(self, _: 'UploadProgressTracking'):
        first_element = self.index(0)
        last_element = self.index(self.rowCount() - 1)
        self.dataChanged.emit(
            first_element,
            last_element,
            [
                QtCore.Qt.ItemDataRole.DisplayRole,
                QtCore.Qt.ItemDataRole.UserRole
            ]
        )