import pathlib
from typing import Iterable, Union
from qtpy import QtWidgets, QtCore

from .ExportView import QtProgress
from ..app import Application
from ..cache import Content
from ..cache import cache as cache_generic




def connectProgressSignals(qprogress):
    # qprogress.valueChanged.connect(lambda x: print(f"{x} bytes downloaded"))
    pass



# async def download_exports()

async def cache(
        app: Application,
        urls: Iterable[str],
        headers: dict[str, str],
        progress: QtProgress
) -> list[Union[Content, Exception]]:
    """
    Downloads URL contents from GRiD

    Parameters
    ----------
    app
    urls
        List of URLs to download the contents of
    headers
        Header information to relay to the GRiD Server

    Returns
    -------

    """
    return await cache_generic(app, urls, headers, progress=progress)
