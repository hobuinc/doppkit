import json
import io
from ntpath import join
import sys
from tokenize import String
import werkzeug
import pathlib
import logging
import httpx
import rich.progress
import asyncio

from io import BytesIO

class Content(object):
    def __init__(self, headers, filename=None, args=None):
        self.filename = filename
        self.directory = None
        self.headers = headers

        if not filename:
            self.filename = self._extract_filename(headers)
        if self.filename:
            try:
                self.directory = args.directory
                self.filename = self.directory.joinpath(self.filename)
            except AttributeError:
                pass

        self._open()
    
    def __exit__(self):
        self.bytes.close()

    def _open(self):
        if not self.filename:
            self.bytes = BytesIO()
        else:
            self.bytes = open(self.filename, 'wb+')
        
        
    def get_data(self):
        self.bytes.flush()
        self.bytes.seek(0)  
        return self.bytes.read()
    data = property(get_data)

    def _extract_filename(self, headers):
        filename = None
        if "Content-Disposition" in headers:
            disposition = headers["Content-Disposition"]
            logging.debug("disposition '%s'" % disposition)
            if "attachment" in disposition.lower():
                # grab Aioysius_PC_20200121.zip from 'attachment; filename="Aioysius_PC_20200121.zip"'
                attachment = werkzeug.http.parse_options_header(
                    headers["Content-Disposition"]
                )
                filename = pathlib.Path(attachment[1]["filename"])
            else:
                filename = None
        return filename

    def save(self):
        logging.debug(f"saving file to {self.filename}")
        if not self.filename:
            raise Exception("Unable to open content object. No filename set")
        with open(self.filename, "wb+") as f:
            f.write(self.bytes.read())

    def __repr__(self):
        return "Content %s %s" % (self.filename, self.headers)

    def __str__(self):
        return self.__repr__()


async def cache(args, urls, headers):

    files = []
    limits = httpx.Limits(
        max_keepalive_connections=args.threads, max_connections=args.threads
    )
    timeout = httpx.Timeout(10.0, connect=20.0)

    session = httpx.AsyncClient(timeout=timeout, limits=limits)
    for url in urls:
        files = await asyncio.gather(
            *[cache_url(args, url, headers, session) for url in urls]
        )
        await session.aclose()
    return files


async def cache_url(args, url, headers, session):

    output = None
    buffer = bytearray()
    with rich.progress.Progress(
        "[progress.percentage]{task.percentage:>3.0f}%",
        rich.progress.BarColumn(bar_width=None),
        rich.progress.DownloadColumn(),
        rich.progress.TransferSpeedColumn(),
    ) as progress:
        with httpx.stream("GET", url, headers=headers) as response:

            if args.progress:
                total = None

                # GRiD doesn't give us this
                if response.headers.get('Content-length'):
                    total = int(response.headers.get('Content-length'))
                download_task = progress.add_task("Download", total=total)
            
            c = Content(response.headers, args=args)
            for chunk in response.iter_bytes():
                count = c.bytes.write(chunk)

                if args.progress:
                    progress.update(download_task, completed=response.num_bytes_downloaded)

            c.bytes.flush()
            c.bytes.seek(0)
            output = c
    return output
