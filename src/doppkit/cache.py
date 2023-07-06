__all__ = ["cache"]

import aiofiles
import contextlib
import pathlib
import logging
import typing
import asyncio

import httpx
from io import BytesIO
from .util import parse_options_header

from typing import Protocol, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from doppkit import Application

class Progress(Protocol):

    def update(self, name: str, completed: int) -> None:
        ...

    def create_task(self, name: str, total: int) -> None:
        ...
    
    def complete_task(self, name: str) -> None:
        ...

class Content:
    def __init__(
        self, headers, filename: typing.Optional[pathlib.Path] = None, args=None
    ):
        self.directory = None
        self.headers = headers

        if filename is None:
            filename = self._extract_filename(headers)

        if isinstance(filename, pathlib.Path):
            with contextlib.suppress(AttributeError):
                self.directory = pathlib.Path(args.directory)
                filename = self.directory.joinpath(filename)

        self.target: typing.Union[BytesIO, pathlib.Path] = (
            BytesIO() if filename is None else filename
        )

    @classmethod
    def _extract_filename(cls, headers) -> typing.Optional[pathlib.Path]:
        filename = None
        if "content-disposition" in [key.lower() for key in headers.keys()]:
            disposition = headers["Content-Disposition"]
            logging.debug(f"disposition '{disposition}'")
            if "attachment" in disposition.lower():
                # grab Aioysius_PC_20200121.zip from 'attachment; filename="Aioysius_PC_20200121.zip"'
                attachment = parse_options_header(headers["Content-Disposition"])
                filename = pathlib.Path(attachment[1]["filename"])
            else:
                filename = None
        return filename

    def __repr__(self):
        return f"Content {self.target} {self.headers}"

    def __str__(self):
        return self.__repr__()

    def get_data(self):
        if isinstance(self.target, BytesIO):
            self.target.flush()
            self.target.seek(0)
            return self.target.read()

        else:
            raise NotImplementedError("data intended to be used with BytesIO objects")

    data = property(get_data)


async def cache(app: 'Application', urls, headers, runner: Optional[asyncio.Runner]=None) -> list[str]:
    limits = httpx.Limits(
        max_keepalive_connections=app.threads, max_connections=app.threads
    )
    timeout = httpx.Timeout(20.0, connect=40.0)

    async with httpx.AsyncClient(
        timeout=timeout, limits=limits, verify=not app.disable_ssl_verification
    ) as client:

        if app.run_method == "CLI":
            from doppkit.rich.cache import cache as cache_method
        elif app.run_method == "GUI":
            from doppkit.qt.cache import cache as cache_method
        else:
            # via API calls no great way to send updates
            # TODO: doesn't iterate over all URLs
            app.progress = False 
            cache_method = cache_url

        files = await cache_method(app, urls, headers, client)

    return files


async def cache_url(args, url, headers, client, progress: Optional[Progress]) -> Content:
    limit = args.limit
    async with limit:
        request = client.build_request("GET", url, headers=headers, timeout=None)
        response = await client.send(request, stream=True)

        filename = None  # placeholder
        total = max(0, int(response.headers.get("Content-length", 0)))
        while response.next_request is not None:
            extracted_filename = Content._extract_filename(response.headers)
            filename = (
                extracted_filename if extracted_filename is not None else filename
            )
            request = response.next_request
            await response.aclose()
            response = await client.send(request, stream=True)
            total = max(total, int(response.headers.get("Content-length", 0)))
        c = Content(response.headers, filename=filename, args=args)
        if args.progress:
            name = c.target.name if isinstance(c.target, pathlib.Path) else "bytesIO"
            progress.add_task(f"{name}", total=total)
        chunk_count = 0
        if isinstance(c.target, BytesIO):
            # do in-memory stuff
            async for chunk in response.aiter_bytes():
                _ = c.target.write(chunk)
                chunk_count += 1

                if args.progress:
                    progress.update(
                        name, completed=response.num_bytes_downloaded
                    )
            c.target.flush()
            c.target.seek(0)
        else:  # isinstance(c.target, pathlib.Path)
            # create parent directory/directories if needed
            if c.target.parent is not None:
                c.target.parent.mkdir(parents=True, exist_ok=True)
            # we are writing to disk asyncronously
            async with aiofiles.open(c.target, "wb+") as f:
                async for chunk in response.aiter_bytes():
                    await f.write(chunk)
                    chunk_count += 1

                    if args.progress:
                        progress.update(
                            name, completed=response.num_bytes_downloaded
                        )
        if args.progress:
            # we can hide the task now that it's finished
            progress.complete_task(name)
        await response.aclose()
        if limit.locked():
            await asyncio.sleep(0.5)
    return c
