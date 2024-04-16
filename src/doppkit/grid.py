__all__ = ["Grid", "Exportfile", "Export", "AOI"]

import itertools
import json
import warnings
import logging
import pathlib
import math

import httpx
from typing import Optional, Iterable, TypedDict, Union, TYPE_CHECKING

from .cache import cache, DownloadUrl, Progress
from .upload import upload

if TYPE_CHECKING:
    from .upload import ETagDict

logger = logging.getLogger(__name__)

API_VERSION = "v4"
MULTIPART_BYTES_PER_CHUNK = 10_000_000  # ~ 6mb

aoi_endpoint_ext = f"/api/{API_VERSION}/aois"
export_endpoint_ext = f"/api/{API_VERSION}/exports"
task_endpoint_ext = f"/api/{API_VERSION}/tasks"
upload_endpoint_ext = f"/api/{API_VERSION}/upload"


class ExportStarted(TypedDict):
    export_id: str
    task_id: str


class Exportfile(TypedDict):
    id: int
    name: str
    datatype: str
    filesize: int
    url: str
    storage_path: str  # isn't present in GRiD v1.7 but will be in following version
    aoi_coverage: float
    geom: str


class Auxfile(TypedDict):
    id: int
    filesize: int
    datatype: str
    name: str
    url: str
    strage_path: str

class Licensefile(TypedDict):
    filesize: int
    url: str
    name: str
    storage_path: str

class VectorProduct(TypedDict):
    id: int


class RasterProduct(TypedDict):
    id: int


class PointcloudProduct(TypedDict):
    id: int


class MeshProduct(TypedDict):
    id: int


class Task(TypedDict):
    name: str
    object_id: int
    state: str
    task_id: int
    time_stamp: str


class Export(TypedDict):

    name: str
    datatype: str
    export_type: str
    exportfiles: Union[list[Exportfile], bool]
    licensefiles: list[Licensefile]
    export_total_size: int
    auxfile_total_size: int
    complete_size: int
    file_export_options: str
    file_format_options: str
    hsrs: Optional[str]
    license_url: str
    notes: str
    percent_complete: str
    id: int
    send_email: bool
    started_at: str
    status: str
    task_id: str
    total_size: int
    url: str
    user: str
    vsrs: Optional[str]
    zip_url: str

Export.__optional_keys__ = frozenset({'export_total_size', 'auxfile_total_size', 'complete_size'})


class AOI(TypedDict):
    id: int
    area: Optional[float]
    name: str
    notes: str
    user: str
    subscribed: bool
    created_at: str
    exports: list[Export]
    raster_intersects: list[RasterProduct]
    mesh_intersects: list[MeshProduct]
    pointcloud_intersects: list[PointcloudProduct]
    vector_intersects: list[VectorProduct]


class Grid:
    def __init__(self, args):
        self.args = args
        # let's quiet down the HTTPX logger
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logger.setLevel(self.args.log_level)

    async def get_aois(self, id: Optional[int]=None) -> list[AOI]:
        logger.debug(f"Getting export information for aoi_pk={id} from {self.args.url}")
        url_args = 'intersections=false&intersection_geoms=false'
        if id:
            url_args += "&export_full=false"
            aoi_endpoint = f"{self.args.url}{aoi_endpoint_ext}/{id}?{url_args}"
        else:
            # Grab full dictionary for the export and parse out the download urls
            url_args += "&export_full=true"
            aoi_endpoint = f"{self.args.url}{aoi_endpoint_ext}?{url_args}"

        # urls = (aoi_endpoint, )
        urls = [DownloadUrl(aoi_endpoint)]
        headers = {"Authorization": f"Bearer {self.args.token}"}
        files = await cache(self.args, urls, headers)
        files = list(files)
        try:
            response = json.load(files[0].target)
        except IndexError as e:
            logger.error(f"GRiD returned no products for AOI {id}")
            raise RuntimeError(f"GRiD returned no products for AOI {id}") from e
        except AttributeError as e:
            if isinstance(files[0], Exception):
                logger.error(f"Doppkit cache function returned the following exception: {files[0]}")
                raise files[0] from e
            elif isinstance(files[0], httpx.Response):
                logger.error(f"{self.args.url} returned the following non-ok response {str(files[0])}")
                raise RuntimeError(f'{files[0]} returned from {self.args.url}') from e
            else:
                logger.error(f"Doppkit cache function returned unexpected type {type(files[0])}")
                raise TypeError(
                    f"Unexpected type {type(files[0])} returned from cache"
                ) from e
        else:
            if "error" in response:
                logger.error(f"GRiD returned the following error: {response['error']}")
                raise RuntimeError(response['error'])
        return response["aois"]


    async def upload_asset(
            self,
            filepath: pathlib.Path,
            directory: Optional[pathlib.Path] = None,
            bytes_per_chunk=MULTIPART_BYTES_PER_CHUNK,
            progress: Optional[Progress]=None
    ):
        logger.info(f"Starting upload of {filepath}")
        source_size = filepath.stat().st_size
        chunks_count = int(math.ceil(source_size / float(bytes_per_chunk)))

        key = ""
        if directory is not None:
            key += f"{directory.as_posix().strip('/')}/"

        key += f"{filepath.name}"
        upload_endpoint_url = f"{self.args.url}{upload_endpoint_ext}"

        headers = {"Authorization": f"Bearer {self.args.token}"}
        async with httpx.AsyncClient(verify=not self.args.disable_ssl_verification) as client:
            params = {"key": key}
            response_upload_id = await client.get(
                f"{upload_endpoint_url}/open/",
                params=params,
                headers=headers
            )
            logger.debug(f"Upload open call returned {response_upload_id}")

            try:
                upload_id = response_upload_id.json()["upload_id"]
            except KeyError as e:
                if "error" in response_upload_id.json():
                    raise ConnectionError(response_upload_id.json()["error"]) from e
                else:
                    raise ConnectionError(response_upload_id.json()) from e

            params.update(upload_id=upload_id, nparts=str(chunks_count))
            response_urls = await client.get(
                f"{upload_endpoint_url}/get_urls/",
                params=params,
                headers=headers
            )

            # want to make sure URLs are in order of part
            urls = [
                part['url'] 
                for part in sorted(
                    response_urls.json()["parts"],
                    key=lambda part: part['part']
                )
            ]

            part_info = await upload(
                app=self.args,
                filepath=filepath,
                urls=urls,
                bytes_per_chunk=bytes_per_chunk,
                auth_header=headers,
                progress=progress
            )

            data = {
                "upload_id": upload_id,
                "key": key,
                "upload_info": part_info
            }

            response_finish = await client.put(
                f"{upload_endpoint_url}/close/",
                json=data,
                headers=headers
            )
            logger.debug(f"Upload close call returned {response_finish}")
            logger.info(f"Finished upload of {filepath}")

        return None


    async def make_exports(
            self,
            aoi: AOI,
            name: str,
            intersect_types:Optional[Iterable[str]]=None
    ) -> list[ExportStarted]:
        """
        Intersect types should be container that includes the combination of:

        * raster
        * vector
        * mesh
        * pointcloud

        defaults to all the above
        """
        if intersect_types is None:
            intersect_types = {"raster", "mesh", "pointcloud", "vector"}
        else:
            intersect_types = set(intersect_types)

        product_ids = []
        for intersection in intersect_types:
            if intersection == "raster":
                product_ids.extend([entry["id"] for entry in aoi["raster_intersects"]])
            elif intersection == "mesh":
                product_ids.extend([entry["id"] for entry in aoi["mesh_intersects"]])
            elif intersection == "pointcloud":
                product_ids.extend([entry["id"] for entry in aoi["pointcloud_intersects"]])
            elif intersection == "vector":
                product_ids.extend([entry["id"] for entry in aoi["vector_intersects"]])
            else:
                warnings.warn(
                    f"Unknown intersect type {intersection}, needs to be one of " +
                    "raster, mesh, pointcloud, or vector.  Ignoring.",
                    stacklevel=2
                )
        export_endpoint = f"{self.args.url}{export_endpoint_ext}"

        # https://pro.arcgis.com/en/pro-app/2.9/arcpy/classes/spatialreference.htm
        # make sure to provide a way to pass in hsrs and vsrs info from arcgis pro
        params = {
            "aoi": str(aoi["id"]),
            "products": ",".join(map(str, product_ids)),
            "name": name,
            'intersections': True,
            'intersection_geoms': False
        }
        headers = {"Authorization": f"Bearer {self.args.token}"}

        async with httpx.AsyncClient(verify=not self.args.disable_ssl_verification) as client:
            r = await client.post(export_endpoint, headers=headers, data=params)

        if r.status_code != httpx.codes.OK:
            raise RuntimeError(f"GRiD Returned an Error: {r.json()['error']}")
        return r.json()["exports"]

    async def check_task(self, task_id: Optional[str] = None) -> list[Task]:
        headers = {"Authorization": f"Bearer {self.args.token}"}
        task_endpoint = f"{self.args.url}{task_endpoint_ext}"
        if task_id is not None:
            task_endpoint += f"/{task_id}"
        params = {"sort": "task_id"}

        async with httpx.AsyncClient(verify=not self.args.disable_ssl_verification) as client:
            r = await client.get(task_endpoint, headers=headers, params=params)

        if r.status_code == httpx.codes.OK:
            output = r.json()["tasks"]
        else:
            logger.warning(f"GRiD task endpoint returned error {r.status_code}")
            raise RuntimeError(f"GRiD Task Endpoint Returned Error {r.status_code}")
        return output

    async def get_exports(self, export_id: int) -> list[DownloadUrl]:
        """
        Parameters
        ----------
        export_id
            Export PK to get a list of Exportfiles for

        Returns
        -------
        list of Exportfile


        """
        # grid.nga.mil/grid/api/v3/exports/56193?file_geoms=false
        export_endpoint = (
            f"{self.args.url}{export_endpoint_ext}/"
            f"{export_id}?file_geoms=false"
        )
        headers = {"Authorization": f"Bearer {self.args.token}"}
        urls = [DownloadUrl(export_endpoint)]
        export_files = await cache(self.args, urls, headers)
        export_files = list(export_files)
        try:
            response = json.load(export_files[0].target)
        except IndexError:
            logger.warning(
                f"Export: {export_id} returned no export files to download"
            )
            return []
        except AttributeError as e:
            if isinstance(export_files[0], Exception):
                logger.error(f"Doppkit Cache Function Returned the following exception: {export_files[0]}")
                raise export_files[0] from e
            elif isinstance(export_files[0], httpx.Response):            
                await export_files[0].aread()
                logger.error(f"GRiD returned an error code {export_files[0].status_code} with message: {export_files[0].text}")
                raise httpx.RequestError from e
            else:
                logger.error(f"Doppkit cache function returned unexpected type: {type(export_files[0])}")
                raise TypeError(
                    f"Cache Function returned unknown type {type(export_files[0])}"
                ) from e
        else:
            if "error" in response:
                logger.warning(
                    f"Attempting to access {export_id=} resulted in the following error " +
                    f"from GRiD: {response['error']}"
                )
                return []

        exports = []
        for f in export_files:
            j = json.loads(f.data)
            exports.append(j)

        files = []
        supplemental_urls = set()
        for e in exports:
            ex = e['exports']
            for item in ex:

                export_id = item["id"]
                for exportfile in iter(item['exportfiles']):
                    # we're dealing with older API before to storage_path attribute
                    # need to construct "storage_path" attribute in exportfiles
                    # currently have to reconstruct from "storage_name"
                    # format is /u02/exports/<userid>/<aoiid>/<exportid>/bits/we/care/about.tif
                    if "storage_path" not in exportfile.keys():
                        exportfile["storage_path"] = (
                            f"./{exportfile['datatype']}"
                            f"{exportfile['storage_name'].rpartition(str(export_id))[-1].rpartition('/')[0]}"
                        )
                    files.append(
                        DownloadUrl(
                            url=exportfile["url"],
                            save_path=f"{item['name']}/{exportfile['storage_path'].strip('/')}/{exportfile['name']}",
                            total=exportfile["filesize"],
                            name=exportfile["name"]
                        )
                    )
                for supplemental_file in itertools.chain(item["auxfiles"], item.get('licensefiles', [])):
                    if supplemental_file["url"] not in supplemental_urls:
                        files.append(
                            DownloadUrl(
                                url=supplemental_file["url"],
                                save_path=f"{item['name']}/{supplemental_file['storage_path'].strip('/')}/{supplemental_file['name']}",
                                total=supplemental_file["filesize"],
                                name=supplemental_file["name"]
                            )
                        )
                        supplemental_urls.add(supplemental_file["url"])
        return files
