import asyncio
import click
import logging
import pathlib

from doppkit.app import Application
from doppkit import __version__

logger = logging.getLogger(__name__)

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
@click.version_option(version=__version__, message=f"doppkit {__version__}")
@click.pass_context
def cli(ctx, token, url, log_level, threads, progress, disable_ssl_verification):

    # Set up logging
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    logging.basicConfig(level=numeric_level)

    # Log program args

    app = Application(
        token=token,
        url=url,
        log_level=log_level,
        threads=threads,
        run_method="CLI",
        progress = progress,
        disable_ssl_verification=disable_ssl_verification
    )
    ctx.obj = app


@cli.command()
@click.pass_obj
@click.option("--timeout", help="Connection timeout", default=20)
@click.option("--start-id", help="Export ID to resume fetching", type=int, default=0)
@click.option(
    "--override",
    default=False,
    is_flag=True,
    type=bool,
    help="Override existing fetches of the same name",
)

@click.option("--directory", help="Output directory to write", default="downloads", type=pathlib.Path)
@click.option("--filter", help="AOI note filter query", default="")
@click.argument("id",)
def sync(app, timeout, start_id, override, directory, filter, id):
    from doppkit.cli.sync import sync as syncFunction
    app.start_id = start_id
    app.timeout = timeout
    app.command = "sync"
    app.override = override
    app.directory = directory
    app.filter = filter
    app.id = id
    asyncio.run(syncFunction(app, id))


@cli.command('list-aois')
@click.option("--filter", help="AOI note filter query", default="")
@click.pass_obj
def listAOIs(app, filter):
    from doppkit.cli.list import listAOIs as listAOIsFunction
    app.filter = filter
    listAOIsFunction(app)


@cli.command('list-exports')
@click.argument("id",  nargs=1)
@click.pass_obj
def listExports(app, id):
    from doppkit.cli.list import listExports as listExportsFunction
    listExportsFunction(app, id)


if __name__ == "__main__":
    cli()
