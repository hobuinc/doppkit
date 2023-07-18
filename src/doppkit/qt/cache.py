import asyncio
import httpx
from typing import Iterable, Union, TYPE_CHECKING
from qtpy import QtWidgets, QtCore


from ..cache import cache_url, Content

if TYPE_CHECKING:
    from ..app import Application

class QtProgress(QtCore.QObject):
    
    taskAdded = QtCore.Signal(object)
    taskRemoved = QtCore.Signal(object)
    

    def __init__(self):
        super().__init__()
        self.tasks: dict[str, QtWidgets.QProgressBar] = {}
    
    def create_task(self, name: str, total: int):
        task = QtWidgets.QProgressBar(None)
        task.setRange(0, total)
        task.setFormat("%v")
        self.taskAdded.emit(task)
        self.tasks[name] = task

    def update(self, name: str, completed: int) -> None:
        task = self.tasks[name]
        task.setValue(completed)
    
    def complete_task(self, name: str) -> None:
        task = self.tasks[name]
        self.taskRemoved.emit(task)


def connectProgressSignals(progress):
    progress.valueChanged.connect(lambda x: print(f"{x} bytes downloaded"))


async def cache(app: 'Application', urls: Iterable[str], headers, client: httpx.AsyncClient) -> list[Union[Content, Exception]]:
    progress = QtProgress()
    progress.taskAdded.connect(connectProgressSignals)
    files = await asyncio.gather(
        *[
            asyncio.create_task(
                cache_url(
                    app,
                    url,
                    headers,
                    client,
                    progress=progress
                )
            )
            for url in urls
        ],
        return_exceptions=True
    )
    return files
