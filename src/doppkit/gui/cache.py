from typing import Iterable, Union, TYPE_CHECKING
import logging

from ..app import Application
from ..cache import Content
from ..cache import DownloadUrl
from ..cache import cache as cache_generic

if TYPE_CHECKING:
    from .window import QtProgress

logger = logging.getLogger(__name__)


async def cache(
        app: Application,
        urls: Iterable[DownloadUrl],
        headers: dict[str, str],
        progress: 'QtProgress'
) -> Iterable[Union[Content, Exception]]:
    """
    Downloads URL contents from GRiD

    Parameters
    ----------
    app
    urls
        List of DownloadUrl Named Tuples to download the contents of
    headers
        Header information to relay to the GRiD Server
    progress
        Progress Interconnect for doppkit cache function to relay
        download progress through.

    Returns
    -------

    """
    return await cache_generic(app, urls, headers, progress=progress)
