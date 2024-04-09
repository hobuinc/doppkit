from typing import Iterable, Union, TYPE_CHECKING
from rich.table import Column
from rich.progress import (
    DownloadColumn,
    Progress,
    BarColumn,
    TextColumn,
    TransferSpeedColumn,
    TaskID
)

from doppkit.cache import cache as cache_generic
if TYPE_CHECKING:
    from ..app import Application
    from ..cache import Content, DownloadUrl


class RichProgress:
    
    def __init__(self, context_manager: Progress):
        self.context_manager = context_manager
        self.tasks: dict[str, TaskID] = {}

    def create_task(self, name: str, source: str, total: int):
        self.tasks[name] = self.context_manager.add_task(name, total=total)

    def update(self, name: str, source: str, completed: int):
        task = self.tasks[name]
        self.context_manager.update(task, completed=completed)
    
    def complete_task(self, name: str, source: str):
        task = self.tasks.pop(name)
        self.context_manager.update(task, visible=False)


async def cache(app: 'Application', urls: Iterable['DownloadUrl'], headers) -> Iterable[Union[Exception, 'Content']]:

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
        files = await cache_generic(app, urls, headers, progress=rich_progress)
    return files
