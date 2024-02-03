import logging
import html
from enum import Enum
import pathlib
from typing import Callable, Optional, List, Dict

from qtpy import QtCore, QtWidgets

logger = logging.getLogger("doppkit")


class LightThemeColors(Enum):
    # Mateiral colors with shade 900
    Red = "#B71C1C"
    Pink = "#FCE4EC"  # (default accent)
    Purple = "#4A148C"
    DeepPurple = "#311B92"
    Indigo = "#1A237E"  # (default primary)
    Blue = "#0D47A1"
    LightBlue = "#01579B"
    Cyan = "#006064"
    Teal = "#004D40"
    Green = "#1B5E20"
    LightGreen = "#33691E"
    Lime = "#827717"
    Yellow = "#F57F17"
    Amber = "#FF6F00"
    Orange = "#E65100"
    DeepOrange = "#BF360C"
    Brown = "#3E2723"
    Grey = "#212121"
    BlueGrey = "#263238"


class DarkThemeColors(Enum):

    Red = "#F44336"
    Pink = "#F48FB1"  # (default accent)
    Purple = "#CE93D8"
    DeepPurple = "#B39DDB"
    Indigo = "#9FA8DA"  # (default primary)
    Blue = "#90CAF9"
    LightBlue = "#81D4FA"
    Cyan = "#80DEEA"
    Teal = "#80CBC4"
    Green = "#A5D6A7"
    LightGreen = "#C5E1A5"
    Lime = "#E6EE9C"
    Yellow = "#FFF59D"
    Amber = "#FFE082"
    Orange = "#FFCC80"
    DeepOrange = "#FFAB91"
    Brown = "#BCAAA4"
    Grey = "#EEEEEE"
    BlueGrey = "#B0BEC5"

class QtSignalContainer(QtCore.QObject):

    signal = QtCore.Signal(str, logging.LogRecord)

class QtLogHandler(logging.Handler):

    old_factory = logging.getLogRecordFactory()
    signal = QtCore.Signal(str, logging.LogRecord)

    def __init__(self, parent: QtCore.QObject, slotFunction: Optional[Callable] = None) -> None:
        super().__init__()
        # needed to resolve PySide issue confusing self.signal.emit and self.emit
        self.qobject = QtSignalContainer(parent)
        self.metaConnect = None
        if slotFunction is not None:
            self.setReceiver(slotFunction)
        logging.setLogRecordFactory(self.record_factory)

    def record_factory(self, *args: List, **kwargs: Dict) -> logging.LogRecord:
        return self.old_factory(*args, **kwargs)

    # def emit(self, *args: list[Union[str, logging.LogRecord]]) -> None:
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.qobject.signal.emit(msg, record)
        return None

    def setReceiver(self, slotFunction: Callable) -> None:
        self.metaConnect = self.qobject.signal.connect(slotFunction, QtCore.Qt.QueuedConnection)


class LoggingDialog(QtWidgets.QDialog):

    colorMap = {
        logging.DEBUG: "Green",
        logging.INFO: "Blue",
        logging.WARNING: "Orange",
        logging.ERROR: "Red",
        logging.CRITICAL: "Purple"
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.resize(900, 400)

        # find the right handler...
        for handler in logger.handlers:
            if isinstance(handler, QtLogHandler):
                self.handler = handler
                break
        else:
            raise RuntimeError("Unable to Find Qt Log Handler")
        
        format_string = "%(name)s %(levelname)-8s %(message)s"
        formatter = logging.Formatter(format_string)
        self.handler.setFormatter(formatter)
        self.handler.setReceiver(self.updateEntries)

        # text viewer
        self.textEdit = QtWidgets.QPlainTextEdit()
        self.textEdit.setReadOnly(True)
        self.textEdit.setBackgroundVisible(False)

        # button box
        stdButton = QtWidgets.QDialogButtonBox.StandardButton
        self.buttonBox = QtWidgets.QDialogButtonBox(
            stdButton.Save | stdButton.Close,
            QtCore.Qt.Orientation.Horizontal
        )
        self.buttonBox.accepted.connect(self.saveToFile)
        self.buttonBox.rejected.connect(self.accept)

        # layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.textEdit)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
    
    def saveToFile(self):
        fileUrl, _ = QtWidgets.QFileDialog.getSaveFileUrl(
            parent=self,
            caption="Save Logfile",
            dir=QtCore.QUrl(
                    QtCore.QStandardPaths.writableLocation(
                        QtCore.QStandardPaths.StandardLocation.HomeLocation
                    )
                ),
            filter="Log File (*.log)",
            supportedSchemes=["file"]
        )

        if fileUrl.isEmpty():
            logger.debug("Cancelled Log Save File Prompt")
            return None

        path = fileUrl.toDisplayString(
            QtCore.QUrl.FormattingOptions(
                QtCore.QUrl.UrlFormattingOption.PreferLocalFile
            )
        )
        logger.info(f"Saving log to {path}")
        pathObj = pathlib.Path(path)
        with open(pathObj, "wt", encoding="utf-8") as f:
            f.write(self.textEdit.toPlainText())
        return None

    def generateHtmlLine(self, color: str, logLevel: str, status: str) -> str:
        left, level, right = map(str.strip, status.partition(logLevel))
        left = f"{left:25}"
        levelHtml = (
            f"<font color={color}>"
            + f"{level:15}"
            + "</font>"
        )
        right = html.escape(right)
        return f"<pre>{left}{levelHtml}{right}</pre>"
    
    @QtCore.Slot(str, logging.LogRecord)
    def updateEntries(self, status: str, record: logging.LogRecord) -> None:
        styleHints = QtWidgets.QApplication.instance().styleHints()
        colorScheme = styleHints.colorScheme

        if colorScheme == QtCore.Qt.ColorScheme.Light:
            colors = LightThemeColors
        else:
            colors = DarkThemeColors
        color = colors[LoggingDialog.colorMap.get(record.levelno, "Grey")].value
        logLevel = logging.getLevelName(record.levelno)
        self.textEdit.appendHtml(self.generateHtmlLine(color, logLevel, status))
