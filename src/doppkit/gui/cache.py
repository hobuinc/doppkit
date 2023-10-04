from typing import Iterable, Union, TYPE_CHECKING
from urllib.parse import urlparse
import logging

from qtpy.QtCore import QSettings

from ..app import Application
from ..cache import Content
from ..cache import cache as cache_generic

if TYPE_CHECKING:
    from .window import QtProgress

logger = logging.getLogger(__name__)

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
    # need to determine if we should skip SSL verification...

    # first, is SSL verification enabled?
    settings = QSettings()
    enable_ssl = settings.value("grid/ssl_verification")
    # if enabled, check the other elements...
    if enable_ssl:
        # check if the GRiD URL is in the white-list
        whiltelisted_urls = settings.value("grid/ssl_url_white_list", [])
        whitelisted_host_names = {urlparse(url).hostname for url in whiltelisted_urls}
        hostname = urlparse(app.url).hostname
        if hostname in whitelisted_host_names:
            enable_ssl = False
    logger.debug(f"Caching with ssl enabled: {enable_ssl}")
    app.disable_ssl_verification = not enable_ssl
    return await cache_generic(app, urls, headers, progress=progress)
