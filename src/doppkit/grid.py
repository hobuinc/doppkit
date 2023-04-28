import json
import asyncio
import httpx
from typing import Dict, Optional, Iterable, List, Union

from .cache import cache as cacheFunction

aoi_endpoint_ext = "/api/v3/aois"
export_endpoint_ext = "/api/v3/exports"
task_endpoint_ext = "/api/v3/tasks"


class Api:
    def __init__(self, args):
        self.args = args

    def get_aois(self, pk=None):
        url_args = 'intersections=true&intersection_geoms=false'
        if pk:
            url_args += "&export_full=false&sort=pk"
            aoi_endpoint = f"{self.args.url}{aoi_endpoint_ext}/{pk}?{url_args}"
        else:
            # Grab full dictionary for the export and parse out the download urls
            url_args += "&export_full=true"
            aoi_endpoint = f"{self.args.url}{aoi_endpoint_ext}?{url_args}"

        urls = (aoi_endpoint, )
        headers = {"Authorization": f"Bearer {self.args.token}"}

        files = asyncio.run(cacheFunction(self.args, urls, headers))
        response = json.load(files[0].target)
        if response.get('error'):
            raise RuntimeError(response['error'])
        return response["aois"]


    async def make_exports(self, aoi: Dict[str, Union[int, str, List[Dict[str, Union[float, int, str]]]]], name: str, intersect_types:Optional[Iterable[str]]=None) -> httpx.Response:
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
            product_pks.extend([entry["pk"] for entry in aoi[f"{intersection}_intersects"]])
        export_endpoint = f"{self.args.url}{export_endpoint_ext}"

        # https://pro.arcgis.com/en/pro-app/2.9/arcpy/classes/spatialreference.htm
        # make sure to provide a way to pass in hsrs and vsrs info from arcgis pro
        params = {
            "aoi": str(aoi["pk"]),
            "products": ",".join(map(str, product_pks)),
            "name": name
        }
        headers = {"Authorization": f"Bearer {self.args.token}"}

        async with httpx.AsyncClient(verify= not self.args.disable_ssl_verification) as client:
            r = await client.post(export_endpoint, headers=headers, data=params)
        return r


    def check_export(self, task_id=None):
        headers = {"Authorization": f"Bearer {self.args.token}"}
        task_endpoint = f"{self.args.url}{task_endpoint_ext}"
        if task_id is not None:
            task_endpoint += f"/{task_id}"
        params = {"sort": "task_id"}
        r = httpx.get(task_endpoint, headers=headers, params=params)
        if r.status_code == httpx.codes.OK:
            output = r.json()["tasks"]
        else:
            raise RuntimeError
        return output


    def get_exports(self, export_pk):

        # grid.nga.mil/grid/api/v3/exports/56193?sort=pk&file_geoms=false
        export_endpoint = f"{self.args.url}{export_endpoint_ext}/{export_pk}?sort=pk&file_geoms=false"
        headers = {"Authorization": f"Bearer {self.args.token}"}
        urls = [export_endpoint]
        files = asyncio.run(cacheFunction(self.args, urls, headers))
        response = json.loads(files[0].data)

        if response.get('error'):
            return None

        exports = []
        for f in files:
            j = json.loads(f.data)
            exports.append(j)

        output = []
        for e in exports:
            ex = e['exports']
            for item in ex:
                output.extend(iter(item['exportfiles']))
        return output

    async def get_exports_async(self, export_pk):
        # # grid.nga.mil/grid/api/v3/exports/56193?sort=pk&file_geoms=false
        # export_endpoint = f"{self.args.url}{export_endpoint_ext}/{export_pk}?sort=pk&file_geoms=false"
        # headers = {"Authorization": f"Bearer {self.args.token}"}
        # urls = [export_endpoint]
        # files = asyncio.run(cacheFunction(self.args, urls, headers))
        # response = json.loads(files[0].data)
        # if response.get('error'):
        #     return None
        #
        # exports = []
        # async for f in files:
        #     j = json.loads(f.data)
        #     exports.append(j)
        #
        # output = []
        # for e in exports:
        #     ex = e['exports']
        #     for item in ex:
        #         output.extend(iter(item['exportfiles']))
        # return output
        raise NotImplementedError
