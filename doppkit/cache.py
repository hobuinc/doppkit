import aiohttp
import asyncio
import json
import io
import sys
import werkzeug
import pathlib


from aiohttp import ClientSession, TCPConnector
import asyncio
import sys
import pypeln as pl

import logging


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
    limit = int(args.threads)

    async with ClientSession(connector=TCPConnector(limit=limit), headers=headers) as session:

        files = []
        async def fetch(url):
            async with session.get(url) as response:

                target = url.rpartition('/')[-1]
                size = int(response.headers.get('content-length', 0)) or None
                logging.debug("response headers '%s'" % response)
                if (response.status != 200):
                    j = await response.json()
                    logging.debug("response '%s'" % j)
                    raise Exception(j)
                buffer = await response.read()
                print(response.headers)
                c = Content(buffer, headers= response.headers)
                files.append(c)

        await pl.task.each(
            fetch, urls, workers=limit,
        )

        return files


