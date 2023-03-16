import collections
import contextlib
import pathlib
import logging
import typing
import httpx
import asyncio


from io import BytesIO
from werkzeug import http
from rich.table import Column
from rich.progress import DownloadColumn, Progress, BarColumn, TextColumn, TransferSpeedColumn

__all__ = ["cache"]

class MyTransport(httpx.AsyncHTTPTransport):

    def __init__(self) -> None:
        # self.memory = memory
        self.memory = []
        super().__init__()

    def handle_async_request(self, request):
        self.memory.append(request.headers)
        return super().handle_async_request(request)


class Content:
    def __init__(self, headers, filename=None, args=None):
        self.filename = filename
        self.directory = None
        self.headers = headers
        if not filename:
            self.filename = self._extract_filename(headers)
        if self.filename:
            with contextlib.suppress(AttributeError):
                self.directory = args.directory
                self.filename = self.directory.joinpath(self.filename)
        self._open()
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.bytes.close()

    def _open(self):
        self.bytes = open(self.filename, 'wb+') if self.filename else BytesIO()

    def get_data(self):
        self.bytes.flush()
        self.bytes.seek(0)  
        return self.bytes.read()
    data = property(get_data)

    def _extract_filename(self, headers) -> typing.Optional[pathlib.Path]:
        filename = None
        if "Content-Disposition" in headers:
            disposition = headers["Content-Disposition"]
            logging.debug(f"disposition '{disposition}'")
            if "attachment" in disposition.lower():
                # grab Aioysius_PC_20200121.zip from 'attachment; filename="Aioysius_PC_20200121.zip"'
                attachment = http.parse_options_header(
                    headers["Content-Disposition"]
                )
                filename = pathlib.Path(attachment[1]["filename"])
            else:
                filename = None
        return filename

    def save(self):
        logging.debug(f"saving file to {self.filename}")
        if not self.filename:
            raise AttributeError("Unable to open content object. No filename set")
        with open(self.filename, "wb+") as f:
            f.write(self.bytes.read())

    def __repr__(self):
        return f"Content {self.filename} {self.headers}"

    def __str__(self):
        return self.__repr__()


async def cache(args, urls, headers):
    limits = httpx.Limits(
        max_keepalive_connections=args.threads, max_connections=args.threads
    )
    timeout = httpx.Timeout(20.0, connect=40.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        follow_redirects=True,
        transport=MyTransport()) as session:

        # breakpoint()
        # text_column = TextColumn('{task.description}', table_column=Column(ratio=1))
        # bar_column = BarColumn(bar_width=None, table_column=Column(ratio=2))
        # with Progress(
        #     "[progress.percentage]{task.percentage:>3.0f}%",
        #     text_column,
        #     bar_column,
        #     DownloadColumn(),
        #     TransferSpeedColumn(),
        # ) as progress:
        files = await asyncio.gather(
            *[cache_url(args, url, headers, session, None) for url in urls]
        )
    return files


async def cache_url(args, url, headers, session, progress):

    output = None
    logging.info(f"fetching url '{url}'")
    async with session.stream("GET", url, headers=headers, timeout=None, follow_redirects=True) as response:
        print(f"{session._transport.memory=}")
        c = Content(response.headers, args=args)

        # if args.progress:
        #     total = None

        #     # GRiD doesn't give us this
        #     if response.headers.get('Content-length'):
        #         total = int(response.headers.get('Content-length'))
        #     name = c.filename
        #     if name:
        #         name = c.filename.name  # just use basename
        #     download_task = progress.add_task(f"{name}", total=total)

        chunk_count = 0
        async for chunk in response.aiter_bytes():
            _ = c.bytes.write(chunk)
            chunk_count = chunk_count + 1

            # if args.progress:
            #     num_bytes = response.num_bytes_downloaded
            #     progress.update(download_task, completed=num_bytes)

    c.bytes.flush()
    c.bytes.seek(0)
    output = c
    return output
