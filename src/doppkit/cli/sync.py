import logging
from pathlib import Path

from doppkit.grid import Grid
from doppkit.cli.cache import cache
from doppkit.cache import Content
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from doppkit.app import Application


logger = logging.getLogger(__name__)

async def sync(args: 'Application', id_: str) -> list[Content]:
    """The main function for our script."""

    # Create a directory into which our downloads will go
    download_dir = Path(args.directory)
    logger.debug(f"download directory: {args.directory}")
    download_dir.mkdir(exist_ok=True)

    api = Grid(args)
    aois = await api.get_aois(int(id_))
    # v3/v4 GRiD API compatabilty 
    key = "id" if "id" in aois[0].keys() else "pk"
    if args.filter:
        logger.debug(f'Filtering AOIs with "{args.filter}"')
        aois = [aoi for aoi in aois if args.filter in aoi["notes"]]
    exportfiles = []
    for aoi in aois:
        for export in aoi["exports"]:
            logger.debug(f"export: {export}")
            files = await api.get_exports(export[key])
            exportfiles.extend(files)
    total_downloads = len(exportfiles)
    count = 0
    urls = []
    logger.debug(f"{total_downloads} files found, downloading to dir: {download_dir}")
    for exportfile in sorted(exportfiles, key=lambda x: int(x.get(key))):
        id_ = exportfile.get(key)
        if id_ < int(args.start_id):
            logger.info(f"Skipping file {id_}")
            total_downloads -= 1
            logger.info(f"{count} of {total_downloads} downloads complete")
            continue
        filename = exportfile["name"]
        download_url = exportfile["url"]
        download_destination = download_dir.joinpath(filename)
        logger.debug(
            f"Exportfile ID {id_} downloading from {download_url} to {download_destination}"
        )

        # Skip this file if we've already downloaded it
        if not args.override and download_destination.exists():
            logger.debug(f"File already exists, skipping: {download_destination}")
        else:
            urls.append(download_url)
    headers = {"Authorization": f"Bearer {args.token}"}
    logger.debug(urls, headers)

    files = await cache(args, urls, headers)
    return files
