import asyncio
import logging
import pathlib
import os

from typing import Union, Optional
from urllib.parse import urlparse

import httpx

class Application:
    def __init__(
            self,
            token: str = None,
            url: str = None,
            log_level=logging.INFO,
            run_method="API",
            threads: int = 20,
            progress: bool = False,
            disable_ssl_verification: bool = False,
            override: bool = False,
            directory: Union[str, pathlib.Path, None] = None,
            filter: str = "",
            start_id: Optional[int] = 0
    ) -> None:
        """_summary_

        Parameters
        ----------
        token : str, optional
            GRiD token to use, if None, it will eventually error, by default None
        url : str, optional
            URL of the grid server to use, by default None
        log_level : logging.Level, optional
            Logging level to set doppkit application to, by default logging.INFO
        run_method : str, optional
            how doppkit is being run, recognized options are CLI, GUI and API, by
            default "API"
        threads : int, optional
            Number of threads to use to download resources, by default 20
        override : bool, optional
            Tells doppkit if the files should be overwritten
        directory: str, pathlib.Path, optional
            Location to download resources
        filter: str
            Filter AOIs that contain the string provided here in the 'notes' field.
            Defaults to empty string, resulting in no filtering of results
        start_id: int
            Filter out AOI PKs below this value.
        """
        self.token = token if token is not None else os.getenv("GRID_ACCESS_TOKEN", "")
        # need to assign the attribute
        self._url = ""
        self.url = url
        self.threads = threads
        self.progress = progress
        self.limit = asyncio.Semaphore(threads)
        self.override = override
        self.run_method = run_method
        self.log_level = log_level

        if not disable_ssl_verification:
            # disable ssl_verification on the following servers:
            # "https://grid.nga.ic.gov" and "https://grid.nga.smil.mil"
            exclude_hosts = set(
                [
                    urlparse(url).hostname
                    for url in ("https://grid.nga.smil.mil", "https://grid.nga.ic.gov")
                ]
            )

            if urlparse(url).hostname in exclude_hosts:
                disable_ssl_verification = True
        self.disable_ssl_verification = disable_ssl_verification
        if directory is None:
            directory = pathlib.Path.home() / "Downloads"
        self.directory = os.fsdecode(directory)
        self.filter = ""
        self.start_id = start_id

    def __repr__(self) -> str:
        return (
            "Doppkit Application\n"
            f"GRid URL {self.url}\n"
            f"Run Method: {self.run_method}\n"
        )

    @property
    def url(self):
        return self._url
    
    @url.setter
    def url(self, url):
        if urlparse(url).path in ["", "/"]:
            # need to get redirect to actual endpoint:
            r = httpx.get(url)
            if r.status_code == 301:
                # aha-sure enough there is a redirect!
                url = str(r.next_request.url)
        self._url = url 
