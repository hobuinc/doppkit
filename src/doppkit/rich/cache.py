import asyncio
from rich.table import Column
from rich.progress import (
    DownloadColumn,
    Progress,
    BarColumn,
    TextColumn,
    TransferSpeedColumn
)

from doppkit.cache import cache_url


async def cache(args, urls, headers, client):

    text_column = TextColumn("{task.description}", table_column=Column(ratio=1))
    bar_column = BarColumn(bar_width=None, table_column=Column(ratio=2))
    with Progress(
        "[progress.percentage]{task.percentage:>3.0f}%",
        text_column,
        bar_column,
        DownloadColumn(),
        TransferSpeedColumn(),
        transient=True
    ) as progress:
        
        files = await asyncio.gather(
            *[
                asyncio.create_task(
                    cache_url(
                        args,
                        url,
                        headers,
                        client,
                        progress
                    )
                )
                for url in urls
            ],
            return_exceptions=True
        )
    return files