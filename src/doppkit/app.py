import asyncio
import click
import logging
import pathlib
import os

from .sync import sync as syncFunction



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
        # self.token: str = os.getenv("GRID_ACCESS_TOKEN", token)
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



@click.group()
@click.option(
    "--token",
    envvar="GRID_ACCESS_TOKEN",
    help="GRiD access token. Use GRID_ACCESS_TOKEN environment variable to globally override",
    type=str,
)
@click.option(
    "--url",
    envvar="GRID_BASE_URL",
    default="https://grid.nga.mil/grid",
    help="GRiD Instance URL. Use GRID_BASE_URL environment variable to globally override",
)
@click.option("--log-level", default="INFO", help="Log level (INFO/DEBUG)")
@click.option("--threads", default=20, type=int, help="Fetch thread count")
@click.option("--progress", default=True, type=bool, help="Report download progress")
@click.option(
    "--disable-ssl-verification",
    default=False,
    is_flag=True,
    type=bool,
    help="Disable SSL verification of URLs",
)
@click.pass_context
def cli(ctx, token, url, log_level, threads, progress, disable_ssl_verification):

    # Set up logging
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    logging.basicConfig(level=numeric_level)

    # Log program args
    logging.debug(f"Log level: {log_level}")

    app = Application(
        token=token,
        url=url,
        log_level=log_level,
        threads=threads,
        run_method="CLI",
        progress = progress
    )
    ctx.obj = app


@cli.command()
@click.pass_obj
@click.option("--timeout", help="Connection timeout", default=20)
@click.option("--start-id", help="Export ID to resume fetching", type=int, default=0)
@click.option(
    "--overwrite",
    default=False,
    is_flag=True,
    type=bool,
    help="Overwrite existing fetches of the same name",
)

@click.option("--directory", help="Output directory to write", default="downloads", type=pathlib.Path)
@click.option("--filter", help="AOI note filter query", default="")
@click.argument("pk",)
def sync(app, timeout, start_id, overwrite, directory, filter, pk):
    app.start_id = start_id
    app.timeout = timeout
    app.command = "sync"
    app.overwrite = overwrite
    app.directory = directory
    app.filter = filter
    app.pk = pk
    asyncio.run(syncFunction(app, pk))


@cli.command('list-aois')
@click.option("--filter", help="AOI note filter query", default="")
@click.pass_obj
def listAOIs(app, filter):
    from .rich.list import listAOIs as listAOIsFunction
    app.filter = filter
    listAOIsFunction(app)


@cli.command('list-exports')
@click.argument("pk",  nargs=1)
@click.pass_obj
def listExports(app, pk):
    from .rich.list import listExports as listExportsFunction
    listExportsFunction(app, pk)
