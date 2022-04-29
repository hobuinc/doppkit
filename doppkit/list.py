
from .grid import Api
import click
import logging
import asyncio
from rich.console import Console
from rich.table import Table

def list(args):
    """List AOIs and Exports for a given user token"""

    api = Api(args)
    aois = api.get_aois()


    console = Console()
    table = Table(title=f'AOIs')

    table.add_column("AOI PK", justify="right")
    table.add_column("Export PK", justify="right")
    table.add_column("Name")
    table.add_column("Export")
    for aoi in aois:
        aoi_pk = str(aoi['pk'])
        name = str(aoi['name'])

        if aoi.get('exports'):
            for export in aoi['exports']:
                export_pk = export['pk']
                exports = api.get_exports(export_pk)
                for e in exports:
                    table.add_row(aoi_pk, str(export_pk), name, e['name'])

    console.print(table)