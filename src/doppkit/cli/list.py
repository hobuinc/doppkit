
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

    table.add_column("AOI PK", justify="right")
    # table.add_column("Export PK", justify="right")
    table.add_column("Name")
    # table.add_column("Export")
    for aoi in aois:
        pk = str(aoi['pk'])
        name = str(aoi['name'])
        table.add_row(pk, name)

    console.print(table)


def listExports(args, pk):
    """List Exports for a given AOI PK"""

    api = Grid(args)

    aois = asyncio.run(api.get_aois(pk=pk))

    aoi = aois[0]
    console = Console()
    table = Table(title=f"Exports for {aoi['name']} – {pk}")

    table.add_column("Export PK")
    table.add_column("Item PK")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Size")
    if aoi.get('exports'):
        for export in aoi['exports']:
            export_pk = export['pk']
            exports =  asyncio.run(api.get_exports(export_pk))
            for e in exports:
                table.add_row(
                    str(export_pk),
                    str(e['pk']),
                    e['name'],
                    e['datatype'],
                    str(e['filesize'])
                )
    console.print(table)
