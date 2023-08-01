from typing import Iterable, Union, TYPE_CHECKING

from ..app import Application
from ..cache import Content
from ..cache import cache as cache_generic

if TYPE_CHECKING:
    from .window import QtProgress


async def cache(
        app: Application,
        urls: Iterable[str],
        headers: dict[str, str],
        progress: 'QtProgress'
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
    progress
        Progress Interconnect for doppkit cache function to relay
        download progress through.

    Returns
    -------

    """
    return await cache_generic(app, urls, headers, progress=progress)
