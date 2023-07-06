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


class RichProgress:
    
    def __init__(self, context_manager):
        self.context_manager = context_manager
        self.tasks: dict[str, object] = {}

    def create_task(self, name: str, total: int):
        self.tasks[name] = self.context_manager.add_task(name, total=total)

    def update(self, name: str, completed: int):
        task = self.tasks[name]
        self.context_manager.update(task, completed)
    
    def complete_task(self, name):
        task = self.tasks[name]
        self.context_manager.update(task, visible=False)
        del self.tasks[name]


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
        
        rich_progress = RichProgress(progress)
        files = await asyncio.gather(
            *[
                asyncio.create_task(
                    cache_url(
                        args,
                        url,
                        headers,
                        client,
                        rich_progress
                    )
                )
                for url in urls
            ],
            return_exceptions=True
        )
    return files