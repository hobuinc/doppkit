__all__ = ["Grid", "Exportfile", "Export", "AOI"]

import json
import warnings
import logging

import httpx
from typing import Optional, Iterable, TypedDict, Union

from .cache import cache


aoi_endpoint_ext = "/api/v3/aois"
export_endpoint_ext = "/api/v3/exports"
task_endpoint_ext = "/api/v3/tasks"


class ExportStarted(TypedDict):
    export_id: str
    task_id: str


class Exportfile(TypedDict):
    pk: int
    name: str
    datatype: str
    filesize: int
    aoi_coverage: float
    geom: str
    url: str


class VectorProduct(TypedDict):
    pk: int

class RasterProduct(TypedDict):
    pk: int

class PointcloudProduct(TypedDict):
    pk: int

class MeshProduct(TypedDict):
    pk: int


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
    export_total_size: int
    auxfile_total_size: int
    complete_size: int
    file_export_options: str
    file_format_options: str
    hsrs: Optional[str]
    license_url: str
    notes: str
    percent_complete: str
    pk: int
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
    pk: int
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

    async def get_aois(self, pk: Optional[int]=None) -> list[AOI]:
        url_args = 'intersections=false&intersection_geoms=false'
        if pk:
            url_args += "&export_full=false&sort=pk"
            aoi_endpoint = f"{self.args.url}{aoi_endpoint_ext}/{pk}?{url_args}"
        else:
            # Grab full dictionary for the export and parse out the download urls
            url_args += "&export_full=true"
            aoi_endpoint = f"{self.args.url}{aoi_endpoint_ext}?{url_args}"

        urls = (aoi_endpoint, )
        headers = {"Authorization": f"Bearer {self.args.token}"}

        files = await cache(self.args, urls, headers)

        try:
            response = json.load(files[0].target)
        except IndexError as e:
            raise RuntimeError(f"GRiD returned no products for AOI {pk}") from e
        except AttributeError as e:
            if isinstance(files[0], Exception):
                raise files[0] from e
            else:
                raise TypeError(
                    f"Unexpected type {type(files[0])} returned from cache"
                ) from e
        else:
            if "error" in response:
                raise RuntimeError(response['error'])
        return response["aois"]


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

        product_pks = []
        for intersection in intersect_types:
            if intersection == "raster":
                product_pks.extend([entry["pk"] for entry in aoi["raster_intersects"]])
            elif intersection == "mesh":
                product_pks.extend([entry["pk"] for entry in aoi["mesh_intersects"]])
            elif intersection == "pointcloud":
                product_pks.extend([entry["pk"] for entry in aoi["pointcloud_intersects"]])
            elif intersection == "vector":
                product_pks.extend([entry["pk"] for entry in aoi["vector_intersects"]])
            else:
                warnings.warn(
                    f"Unknown intersect type {intersection}, needs to be one of "
                    "raster, mesh, pointcloud, or vector.  Ignoring.",
                    stacklevel=2
                )
        export_endpoint = f"{self.args.url}{export_endpoint_ext}"

        # https://pro.arcgis.com/en/pro-app/2.9/arcpy/classes/spatialreference.htm
        # make sure to provide a way to pass in hsrs and vsrs info from arcgis pro
        params = {
            "aoi": str(aoi["pk"]),
            "products": ",".join(map(str, product_pks)),
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
            raise RuntimeError(f"GRiD Taskpoint Endpoint Returned Error {r.status_code}")
        return output


    async def get_exports(self, export_pk: int) -> list[Exportfile]:
        """
        Parameters
        ----------
        export_pk
            Export PK to get a list of Exportfiles for

        Returns
        -------
        list of Exportfile


        """
        # grid.nga.mil/grid/api/v3/exports/56193?sort=pk&file_geoms=false
        export_endpoint = (
            f"{self.args.url}{export_endpoint_ext}/"
            f"{export_pk}?sort=pk&file_geoms=false"
        )
        headers = {"Authorization": f"Bearer {self.args.token}"}
        urls = [export_endpoint]
        export_files = await cache(self.args, urls, headers)
        try:
            response = json.load(export_files[0].target)
        except IndexError:
            warnings.warn(
                f"Export: {export_pk} returned no export files to download",
                stacklevel=2
            )
            return []
        except AttributeError as e:
            if isinstance(export_files[0], Exception):
                raise export_files[0] from e
            else:
                raise TypeError(
                    f"Cache Function returned unknown type {type(export_files[0])}"
                ) from e
        else:
            if "error" in response:
                warnings.warn(
                    f"Attempting to access {export_pk=} resulted in the following error "
                    f"from GRiD: {response['error']}",
                    stacklevel=2
                )
                return []

        exports = []
        for f in export_files:
            j = json.loads(f.data)
            exports.append(j)

        export_files = []
        for e in exports:
            ex = e['exports']
            for item in ex:
                export_files.extend(iter(item['exportfiles']))
        return export_files
