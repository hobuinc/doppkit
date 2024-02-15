
import asyncio
from doppkit.grid import Grid
from rich.console import Console
from rich.table import Table


def listAOIs(args):
    """List AOIs and Exports for a given user token"""

    api = Grid(args)
    aois = asyncio.run(api.get_aois())

    console = Console()
    table = Table(title='AOIs')

    table.add_column("AOI ID", justify="right")
    table.add_column("Name")
    for aoi in aois:
        id_ = str(aoi['id'])
        name = str(aoi['name'])
        table.add_row(id_, name)

    console.print(table)


def listExports(args, id_):
    """List Exports for a given AOI ID"""

    api = Grid(args)

    aois = asyncio.run(api.get_aois(id_=id_))

    aoi = aois[0]
    console = Console()
    table = Table(title=f"Exports for {aoi['name']} – {id_}")

    table.add_column("Export ID")
    table.add_column("Name")
    table.add_column("Size")
    if aoi.get('exports'):
        for export in aoi['exports']:
            export_id = export['id']
            exports = asyncio.run(api.get_exports(export_id))
            for e in exports:
                table.add_row(
                    str(export_id),
                    e.name,
                    str(e.total)
                )
    console.print(table)
