import asyncio
import contextlib
from importlib import resources
import logging
import os
import signal
import sys
from qtpy import QtWidgets, QtGui

import qasync
from doppkit.gui.window import Window
from doppkit.gui.LogWidget import QtLogHandler
from doppkit.app import Application

logger = logging.getLogger("doppkit")


async def start_gui(app: 'Application'):

    loop = asyncio.get_event_loop()
    future = loop.create_future()

    qApp: QtWidgets.QApplication = QtWidgets.QApplication.instance()
    qApp.setApplicationName("doppkit")
    qApp.setOrganizationName("Hobu")
    qApp.setStyle("fusion")

    qt_handler = QtLogHandler(qApp)
    logger.addHandler(qt_handler)

    # TODO remove debug log handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(app.log_level)
    formatter = logging.Formatter("%(name)-35s: %(levelname)-8s %(message)s")
    stream_handler.setFormatter(formatter)
    logger.setLevel(app.log_level)
    logger.addHandler(stream_handler)
    # END debug log handler block

    icon_path = os.path.join(
        str(resources.files("doppkit.gui.resources")),
        "grid-icon.ico"
    )

    qApp.setWindowIcon(
        QtGui.QIcon(
            icon_path
        )
    )
    window = Window(app)

    # inspired by:
    # https://github.com/Debianissimo/instart/blob/3d90083de27b078fb1295bd407f4f1a27fd582e3/instart/frontend.py#L582
    def close(*args):
        loop.call_later(10, future.cancel)
        future.cancel()
        loop.stop()

    signal.signal(signal.SIGINT, close)
    signal.signal(signal.SIGTERM, close)
    qApp.aboutToQuit.connect(close)
    with contextlib.suppress(asyncio.CancelledError):
        await future
    return True


def main():
    app = Application(
        token=None,
        url="https://grid.nga.mil/grid",
        log_level=logging.DEBUG,  # override for custom messaging
        threads=5,
        run_method="GUI",
        progress=True,
        override=False
    )
    # https://github.com/CabbageDevelopment/qasync/issues/68
    # the easy way breaks with Python 3.11, so we do the plumbing ourselves to work around it
    if sys.version_info.major == 3 and sys.version_info.minor == 11:
        with qasync._set_event_loop_policy(qasync.DefaultQEventLoopPolicy()):
            runner = asyncio.runners.Runner()
            try:
                runner.run(start_gui(app))
            finally:
                runner.close()
    else:
        qasync.run(start_gui(app))


if __name__ == "__main__":
    main()
