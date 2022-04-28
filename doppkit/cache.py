import json
import io
import sys
import werkzeug
import pathlib
import logging
import httpx
import rich.progress
import asyncio


class Content(object):
    def __init__(self, bytes,
                 headers = None):
        self.filename = 'dummy'
        self.bytes = bytes
        self.headers = headers
        if 'Content-Disposition' in self.headers:
            disposition = self.headers['Content-Disposition']
            logging.debug("disposition '%s'" % disposition)
            if 'attachment' in disposition.lower():
                # grab Aioysius_PC_20200121.zip from 'attachment; filename="Aioysius_PC_20200121.zip"'
                attachment = werkzeug.http.parse_options_header(self.headers['Content-Disposition'])
                self.filename = attachment[1]['filename']
    def save(self, path):
        logging.debug(f"saving file to {path} {self.filename}" )
        with open(path.joinpath(self.filename), 'wb') as f:
            f.write(self.bytes)
    def __repr__(self):
        return 'Content %s %s' % (self.filename, self.headers)
    def __str__(self):
        return self.__repr__()


async def cache(args, urls, headers):
    
    files = []
    limits = httpx.Limits(max_keepalive_connections=args.threads/2, 
                          max_connections=args.threads)
    timeout = httpx.Timeout(10.0, connect=20.0)

    for url in urls:
        session = httpx.AsyncClient(timeout = timeout, limits = limits)
        files = await asyncio.gather(*[cache_url(args, url, headers, session) for url in urls])
        await session.aclose()
    return files

async def cache_url(args, url, headers, session):
    
    output = None
    buffer = bytearray()
    with httpx.stream("GET", url, headers=headers) as response:

        with rich.progress.Progress(
            "[progress.percentage]{task.percentage:>3.0f}%",
            rich.progress.BarColumn(bar_width=None),
            rich.progress.DownloadColumn(),
            rich.progress.TransferSpeedColumn(),
        ) as progress:
            download_task = progress.add_task("Download", total=None)
            for chunk in response.iter_bytes():
                buffer += chunk
                progress.update(download_task, completed=response.num_bytes_downloaded)

            c = Content(buffer, headers= response.headers)
            output = c
    return output


