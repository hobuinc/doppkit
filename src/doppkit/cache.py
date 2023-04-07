import aiofiles
import contextlib
import pathlib
import logging
import typing
import httpx
import asyncio

from io import BytesIO
from werkzeug import http
from rich.table import Column
from rich.progress import (
    DownloadColumn,
    Progress,
    BarColumn,
    TextColumn,
    TransferSpeedColumn,
)

__all__ = ["cache"]


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
                self.directory = args.directory
                filename = self.directory.joinpath(filename)

        self.target: BytesIO | pathlib.Path = (
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
                attachment = http.parse_options_header(headers["Content-Disposition"])
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


async def cache(args, urls, headers):
    limits = httpx.Limits(
        max_keepalive_connections=args.threads, max_connections=args.threads
    )
    timeout = httpx.Timeout(20.0, connect=40.0)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        text_column = TextColumn("{task.description}", table_column=Column(ratio=1))
        bar_column = BarColumn(bar_width=None, table_column=Column(ratio=2))
        with Progress(
            "[progress.percentage]{task.percentage:>3.0f}%",
            text_column,
            bar_column,
            DownloadColumn(),
            TransferSpeedColumn(),
            transient=True,
        ) as progress:

            files = await asyncio.gather(
                *[asyncio.create_task(
                    cache_url(
                        args,
                        url,
                        headers,
                        client,
                        progress,
                    )
                ) for url in urls],
                return_exceptions=True,
            )
    return files


async def cache_url(args, url, headers, client, progress):
    limit = args.limit
    async with limit:
        request = client.build_request("GET", url, headers=headers, timeout=None)
        response = await client.send(request, stream=True)


        filename = None  # placeholder
        total = max(0, int(response.headers.get("Content-length", 0)))

        while response.next_request is not None:
            extracted_filename = Content._extract_filename(response.headers)
            filename = extracted_filename if extracted_filename is not None else filename
            request = response.next_request
            await response.aclose()
            response = await client.send(request, stream=True)
            total = max(total, int(response.headers.get("Content-length", 0)))

        c = Content(response.headers, filename=filename, args=args)
        if args.progress:
            name = c.target.name if isinstance(c.target, pathlib.Path) else "bytesIO"
            download_task = progress.add_task(f"{name}", total=total)
        chunk_count = 0

        if isinstance(c.target, BytesIO):
            # do in-memory stuff
            async for chunk in response.aiter_bytes():
                _ = c.target.write(chunk)
                chunk_count += 1

                if args.progress:
                    progress.update(download_task, completed=response.num_bytes_downloaded)
            c.target.flush()
            c.target.seek(0)

        else:
            # we are writing to disk asyncronously
            async with aiofiles.open(c.target, "wb+") as f:
                async for chunk in response.aiter_bytes():
                    await f.write(chunk)
                    chunk_count += 1

                    if args.progress:
                        progress.update(
                            download_task, completed=response.num_bytes_downloaded
                        )
        if args.progress:
            # we can hide the task now that it's finished
            progress.update(download_task, visible=False)
        await response.aclose()
        if limit.locked():
            await asyncio.sleep(0.5)
    return c
