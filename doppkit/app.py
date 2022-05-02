import configparser

import click
import logging
import pathlib

from .sync import sync as syncFunction
from .list import listAOIs as listAOIsFunction
from .list import listExports as listExportsFunction


class Application(object):
    def __init__(self, token=None, url=None, log_level=logging.ERROR, threads = 20):
        self.token = token
        self.url = url
        self.log_level = log_level
        self.threads = threads


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
    help="GRiD Instance URL. Use GRID_BASE_URL environment variable to gobally override",
)
@click.option("--log-level", default="INFO", help="Log level (INFO/DEBUG)")
@click.option("--threads", default=20, type=int, help="Fetch thread count")
@click.option("--progress", default=True, type=bool, help="Report download progress")
@click.pass_context
def cli(ctx, token, url, log_level, threads, progress):

    # Set up logging
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % loglevel)
    logging.basicConfig(level=numeric_level)

    # Log program args
    logging.debug(f"Log level: {log_level}")

    app = Application(token, url, log_level, threads)
    app.logging = logging
    app.progress = progress

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
@click.option("--pk", help="AOI primary key to sync", default=None)
def sync(app, timeout, start_id, overwrite, directory, filter, pk):
    app.start_id = start_id
    app.timeout = timeout
    app.command = "sync"
    app.overwrite = overwrite
    app.directory = directory
    app.filter = filter
    app.pk = pk
    syncFunction(app)


@cli.command('list-aois')
@click.option("--filter", help="AOI note filter query", default="")
@click.pass_obj
def listAOIs(app, filter):
    app.filter = filter
    listAOIsFunction(app)

@cli.command('list-exports')
@click.argument("pk",  nargs=1)
@click.pass_obj
def listExports(app, pk):
    listExportsFunction(app, pk)
