__all__ = ["Content", "Progress", "cache", "cache_url", "DownloadUrl"]

import aiofiles
import contextlib
import pathlib
import logging
import asyncio
import shutil
import httpx
from io import BytesIO
from .util import parse_options_header
from . import __version__

from typing import Protocol, Optional, NamedTuple, TYPE_CHECKING, Union, Iterable

if TYPE_CHECKING:
    from .app import Application

logger = logging.getLogger(__name__)


class DownloadUrl(NamedTuple):
    url: str
    name: str = ""
    save_path: str = "."
    total: int = 1


class Progress(Protocol):

    def update(self, name: str, source: str, completed: int) -> None:
        ...

    def create_task(self, name: str, source: str, total: int) -> None:
        ...
    
    def complete_task(self, name: str, source: str) -> None:
        ...




class Content:
    def __init__(
        self,
        headers,
        filename: Optional[pathlib.Path] = None,
        args: 'Optional[Application]' = None
    ):
        self.directory = None
        self.headers = headers

        if filename is None:
            filename = self._extract_filename(headers)

        if isinstance(filename, pathlib.Path):
            with contextlib.suppress(AttributeError):
                self.directory = pathlib.Path(args.directory)
                filename = self.directory.joinpath(filename)

        self.target: Union[BytesIO, pathlib.Path] = (
            BytesIO() if filename is None else filename
        )

    @classmethod
    def _extract_filename(cls, headers) -> Optional[pathlib.Path]:
        filename = None
        if "content-disposition" in [key.lower() for key in headers.keys()]:
            disposition = headers["Content-Disposition"]
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

    def get_data(self) -> bytes:
        if isinstance(self.target, BytesIO):
            self.target.flush()
            self.target.seek(0)
            return self.target.read()
        else:
            raise NotImplementedError("data intended to be used with BytesIO objects")

    data = property(get_data)


completed_downloads: dict[str, Content] = dict()


async def cache(
        app: 'Application',
        urls: Iterable[DownloadUrl],
        headers: dict[str, str],
        progress: Optional[Progress] = None
) -> Iterable[Union[Content, BaseException, httpx.Response]]:
    limits = httpx.Limits(
        max_keepalive_connections=app.threads, max_connections=app.threads
    )
    timeout = httpx.Timeout(20.0, connect=40.0)
    headers['user-agent'] = f"doppkit/{__version__}/{app.run_method}"
    headers["Authorization"] = f"Bearer {app.token}"
    async with httpx.AsyncClient(
        timeout=timeout, limits=limits, verify=not app.disable_ssl_verification
    ) as client:
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
    logger.info(f"Cache operation complete for {len(files)} files.")
    return files


async def cache_url(
        args: 'Application',
        url: DownloadUrl,
        headers: dict[str, str],
        client: httpx.AsyncClient,
        progress: Optional[Progress] = None
) -> Union[Content, httpx.Response]:
    limit = args.limit
    async with limit:
        if url.name:
            logger.info(f"Getting {url.name}...")
        request = client.build_request("GET", url.url, headers=headers, timeout=None)
        response = await client.send(request, stream=True)
        if response.is_error:
            await response.aread()
            logger.error(f"GRiD returned an error code {response.status_code} with message: {response.text}")
            return response

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
        if filename is not None:  # we are not saving to BytesIO
            filename = pathlib.Path(url.save_path.lstrip("/"))
        c = Content(
            response.headers,
            filename=filename,
            args=args
        )
        if args.progress and progress is not None:
            name = c.target.name if isinstance(c.target, pathlib.Path) else "bytesIO"
            progress.create_task(f"{name}", url.url, total=total)
        chunk_count = 0
        if isinstance(c.target, BytesIO):
            # do in-memory stuff
            async for chunk in response.aiter_bytes():
                _ = c.target.write(chunk)
                chunk_count += 1
                if args.progress and progress is not None:
                    progress.update(
                        name, url.url, completed=response.num_bytes_downloaded
                    )
            c.target.flush()
            c.target.seek(0)
        else:
            # isinstance(c.target, pathlib.Path)
            # create parent directory/directories if needed
            if c.target.parent is not None:
                c.target.parent.mkdir(parents=True, exist_ok=True)

            # check if we already downloaded this asset
            if url.url in completed_downloads:
                # get the path stored previously
                previous_content = completed_downloads[url.url]
                logger.info(f"Download cache hit on {c.target.name}, copying from {previous_content.target}")
                shutil.copy(previous_content.target, c.target)
            else:
                # we are writing to disk asynchronously
                async with aiofiles.open(c.target, "wb+") as f:
                    async for chunk in response.aiter_bytes():
                        await f.write(chunk)
                        chunk_count += 1
                        if args.progress and progress is not None:
                            progress.update(
                                name,
                                url.url,
                                completed=response.num_bytes_downloaded
                            )
                completed_downloads[url.url] = c

        if args.progress and progress is not None:
            # we can hide the task now that it's finished
            progress.complete_task(name, url.url)
        await response.aclose()
        if limit.locked():
            await asyncio.sleep(0.5)
    return c
