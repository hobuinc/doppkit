import configparser

import click
import logging

from .sync import sync as syncFunction


class Application(object):
    def __init__(self, token=None, url=None, log_level=logging.ERROR):
        self.token = token
        self.url = url
        self.log_level = log_level


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
@click.pass_context
def cli(ctx, token, url, log_level):
    ctx.obj = Application(token, url, log_level)


@cli.command()
@click.pass_obj
@click.option("--threads", default=20, type=int, help="Fetch thread count")
@click.option("--timeout", help="Connection timeout", default=20)
@click.option("--start-id", help="Export ID to resume fetching", type=int, default=0)
@click.option(
    "--overwrite",
    default=False,
    type=bool,
    help="Overwrite existing fetches of the same name",
)
@click.option("--directory", help="Output directory to write", default="downloads")
@click.option("--filter", help="AOI note filter query", default="")
def sync(app, threads, timeout, start_id, overwrite, directory, filter):
    app.threads = threads
    app.start_id = start_id
    app.timeout = timeout
    app.command = "sync"
    app.overwrite = overwrite
    app.directory = directory
    app.filter = filter
    syncFunction(app)


@cli.command()
@click.pass_obj
def list(app):
    click.echo(f"{app}")
    click.echo("listing")
