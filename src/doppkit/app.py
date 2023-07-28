import asyncio
import logging
import pathlib
import os


class Application:
    def __init__(
            self,
            token: str=None,
            url: str=None,
            log_level=logging.ERROR,
            run_method="API",
            threads: int=20,
            progress: bool = False,
            disable_ssl_verification: bool = False,
            override: bool = False
        ) -> None:
        """_summary_

        Parameters
        ----------
        token : str, optional
            GRiD token to use, if None, it will eventually error, by default None
        url : str, optional
            URL of the grid server to use, by default None
        log_level : logging.Level, optional
            Logging level to set doppkit application to, by default logging.ERROR
        run_method : str, optional
            how doppkit is being run, recognized options are CLI, GUI and API, by default "API"
        threads : int, optional
            Number of threads to use to download resources, by default 20
        override : bool, optional
            Tells doppkit if the files should be overwritten
        """
        self.token = token if token is not None else os.getenv("GRID_ACCESS_TOKEN", "")
        self.url = url
        self.threads = threads
        self.progress = progress
        self.limit = asyncio.Semaphore(threads)
        self.override = override

        self.run_method = run_method
        self.log_level = log_level
        self.disable_ssl_verification = disable_ssl_verification
        self.directory = os.fsdecode(pathlib.Path.home() / "Downloads")
    
    def __repr__(self) -> str:
        return (
            "Doppkit Application\n"
            f"GRid URL {self.url}\n"
            f"URL: {self.url}\n"
            f"Run Method: {self.run_method}\n"
        )
