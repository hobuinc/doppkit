import logging
from pathlib import Path

from doppkit.grid import Grid
from doppkit.cli.cache import cache
from doppkit.cache import Content, DownloadUrl
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from doppkit.app import Application


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def sync(args: 'Application', id_: str) -> Iterable[Content]:
    """The main function for our script."""

    # Create a directory into which our downloads will go
    download_dir = Path(args.directory)
    logger.debug(f"download directory: {args.directory}")
    download_dir.mkdir(exist_ok=True)

    api = Grid(args)
    aois = await api.get_aois(int(id_))

    if args.filter:
        logger.debug(f'Filtering AOIs with "{args.filter}"')
        aois = [aoi for aoi in aois if args.filter in aoi["notes"]]
    files_to_download = []
    for aoi in aois:
        for export in aoi["exports"]:
            logger.debug(f"export: {export}")
            files = await api.get_exports(export["id"])
            files_to_download.extend(files)

    total_downloads = len(files_to_download)
    urls = []
    logger.debug(f"{total_downloads} files found, downloading to dir: {download_dir}")
    for file_ in files_to_download:
        download_url = file_.url
        download_destination = download_dir.joinpath(file_.save_path)
        logger.debug(
            f"File {file_.name} downloading from {download_url} to {download_destination}"
        )
        # Skip this file if we've already downloaded it
        if not args.override and download_destination.exists():
            logger.debug(f"File already exists, skipping: {download_destination}")
        else:
            urls.append(
                file_
            )
    headers = {"Authorization": f"Bearer {args.token}"}
    logger.debug(urls, headers)

    files = await cache(args, urls, headers)
    return files
