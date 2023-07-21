import logging
from pathlib import Path

from .grid import Grid
from .rich.cache import cache


async def sync(args, pk: str):
    """The main function for our script."""

    # Create a directory into which our downloads will go
    download_dir = Path(args.directory)
    logging.debug(f"download directory: {args.directory}")
    download_dir.mkdir(exist_ok=True)

    api = Grid(args)
    aois = await api.get_aois(int(pk))
    if args.filter:
        logging.debug(f'Filtering AOIs with "{args.filter}"')
        aois = [aoi for aoi in aois if args.filter in aoi["notes"]]
    exportfiles = []
    for aoi in aois:
        for export in aoi["exports"]:
            logging.debug(f"export: {export}")
            files = await api.get_exports(export['pk'])
            exportfiles.extend(files)
    total_downloads = len(exportfiles)
    count = 0
    urls = []
    logging.debug(f"{total_downloads} files found, downloading to dir: {download_dir}")
    for exportfile in sorted(exportfiles, key=lambda x: int(x.get("pk"))):
        pk = exportfile.get("pk")
        if pk < int(args.start_id):
            logging.info(f"Skipping file {pk}")
            total_downloads -= 1
            logging.info(f"{count} of {total_downloads} downloads complete")
            continue
        filename = exportfile["name"]
        download_url = exportfile["url"]
        download_destination = download_dir.joinpath(filename)
        logging.debug(
            f"Exportfile PK {pk} downloading from {download_url} to {download_destination}"
        )

        # Skip this file if we've already downloaded it
        if not args.overwrite and download_destination.exists():
            logging.debug(f"File already exists, skipping: {download_destination}")
        else:
            urls.append(download_url)
    headers = {"Authorization": f"Bearer {args.token}"}
    logging.debug(urls, headers)

    _ = await cache(args, urls, headers)
