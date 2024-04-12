__all__ = ["upload"]

import aiofiles
import pathlib
import logging
import asyncio
import os
import httpx
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

from typing import TypedDict, Optional

from .cache import Progress
from .app import Application

class ETagDict(TypedDict):
    ETag: str
    PartNumber: int

logger = logging.getLogger(__name__)

file_shared_lock = asyncio.Lock()
part_info = defaultdict(list)
async def upload(
        app: 'Application',
        filepath: pathlib.Path,
        urls: list[str],
        bytes_per_chunk:int,
        auth_header: dict[str, str],
        progress: Optional[Progress] = None
) -> list[ETagDict]:
    
    part_info[filepath].clear()
    tasks = []
    source_size = filepath.stat().st_size
    if progress is not None:
        progress.create_task(
            filepath.name,
            filepath.as_posix(),
            total=source_size
        )
    async with httpx.AsyncClient() as client:
        async with aiofiles.open(filepath, mode='rb') as f:
            tasks.extend(
                upload_chunk(
                    app=app,
                    client=client,
                    file_buffer=f,
                    file_path=filepath,
                    chunk_number=chunk_number,
                    bytes_per_chunk=bytes_per_chunk,
                    source_size=source_size,
                    url=url,
                    auth_header=auth_header,
                    progress=progress
                )
                for chunk_number, url in enumerate(urls)
            )
            await asyncio.gather(*tasks)
    parts = part_info[filepath].copy()
    # grid needs this list sorted by part number
    parts.sort(key=lambda part: part["PartNumber"])
    if app.progress and progress is not None:
        progress.complete_task(filepath.name, filepath.as_posix())
    return parts

async def upload_chunk(
    app: 'Application',
    client: httpx.AsyncClient,
    file_buffer: aiofiles.threadpool.binary.AsyncBufferedReader,
    file_path: pathlib.Path,
    chunk_number: int,
    bytes_per_chunk: int,
    source_size: int,
    url: str,
    auth_header: dict[str, str],
    progress: Optional[Progress] = None
):
    offset = chunk_number * bytes_per_chunk
    remaining_bytes = source_size - offset
    bytes_to_read = min([bytes_per_chunk, remaining_bytes])
    
    part_number = chunk_number + 1
    parsed = urlparse(url)
    qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    path = f'{parsed.scheme}://{parsed.netloc}{parsed.path}'
    
    auth_header['CONTENT_TYPE'] = 'application/json'
    auth_header["HTTP_AUTHORIZATION"] = auth_header["Authorization"]
    r = await client.put(
        path,
        json=qs,
        headers=auth_header,
    )
    url = r.next_request.url

    async with file_shared_lock:
        await file_buffer.seek(offset)
        chunk = await file_buffer.read(bytes_to_read)

    headers = {
        'Content-Length': f'{bytes_to_read}'
    }
    
    attempt = 0
    while attempt < 10:
        try:
            response = await client.put(
                url,
                content=chunk,
                timeout=None,
                headers=headers
            )
        except httpx.ReadError:
            await asyncio.sleep(1.1 ** attempt)
            attempt += 1
            continue
        else:
            break
    else:
        raise httpx.ReadError

    if app.progress and progress is not None:
        old_progress = progress.upload_progress[file_path.as_posix()]
        new_completition = old_progress.current + bytes_to_read
        progress.update(
            os.path.basename(file_path),
            file_path.as_posix(),
            completed=new_completition
        )
    logger.debug(f"Finished uploading chunk {part_number} of {file_path.as_posix()}")

    part_info[file_path].append(
        {
            'PartNumber': part_number,
            'ETag': response.headers['etag']
        }
    )
