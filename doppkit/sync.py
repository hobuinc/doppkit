import json
import os
import sys
import logging
import aiohttp
import asyncio

from argparse import ArgumentParser
from urllib.request import urlopen, Request
from pathlib import Path

from .cache import cache
from .grid import Api


def sync(args, pk):
    """The main function for our script."""

    # Create a directory into which our downloads will go
    download_dir = Path(args.directory)
    logging.debug(f"download directory: {args.directory}")
    download_dir.mkdir(exist_ok=True)

    api = Api(args)

    aois = api.get_aois(pk)


    if args.filter:
        logging.debug(f'Filtering AOIs with "{args.filter}"')
        aois = [aoi for aoi in aois if args.filter in aoi["notes"]]

    exportfiles = []
    for aoi in aois:
        for export in aoi["exports"]:
            logging.debug(f"export: {export}")
            files = api.get_exports(export['pk'])
            exportfiles.extend(files)

    total_downloads = len(exportfiles)
    count = 0
    urls = []
    logging.info(f"{total_downloads} files found, downloading to dir: {download_dir}")
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
        logging.debug(f"download destination: {download_destination}")
        logging.info(
            f"Exportfile PK {pk} downloading from {download_url} to {download_destination}"
        )

        # Skip this file if we've already downloaded it
        if not args.overwrite and download_destination.exists():
            logging.info(f"File already exists, skipping: {download_destination}")
        else:
            # TODO FIXME
            download_url = download_url.replace("http", "https")
            download_url = download_url.replace("httpss", "https")
            urls.append(download_url)

    headers = {"Authorization": f"Bearer {args.token}"}
    logging.debug(urls, headers)

    files = asyncio.run(cache(args, urls, headers))

